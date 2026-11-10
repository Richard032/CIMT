"""Application guides use synthetic observations and no external services."""

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from app_knowledge import AppKnowledge
from errors import InfrastructureError
from redaction import Redactor


class AppKnowledgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = Mock()
        self.repository.read.return_value = None
        self.knowledge = AppKnowledge({}, dict(report=str(self.root), runId='run-1', sourceCommit='abc123'),
            Redactor({'credentials': {'account': {'password': 'private-value'}}}), self.repository)
        self.device = dict(platform='ios', id='private-device-id')
        self.session = SimpleNamespace(app_id='org.example.app', application_knowledge={'guide': ''},
            learned_app_knowledge='Open Settings, then choose Tier. private-value', result={'steps': [{}, {}]})

    def test_matching_guide_is_loaded_with_identity_and_redacted_text(self):
        self.repository.read.return_value = dict(schemaVersion=1, appId='org.example.app', platform='ios',
            guide='Use Settings. private-value')
        result = self.knowledge.load('org.example.app', 'ios')
        self.repository.read.assert_called_once_with('knowledge/apps/ios/org.example.app.json')
        self.assertEqual(result['status'], 'loaded')
        self.assertEqual(result['guide'], 'Use Settings. <redacted>')
        self.assertEqual(result['appId'], 'org.example.app')

    def test_mismatched_identity_is_unavailable_without_exposing_guide(self):
        self.repository.read.return_value = dict(schemaVersion=1, appId='another.app', platform='ios', guide='Wrong app')
        result = self.knowledge.load('org.example.app', 'ios')
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['guide'], '')

    def test_malformed_provenance_does_not_stop_testing(self):
        self.repository.read.return_value = dict(schemaVersion=1, appId='org.example.app', platform='ios',
            guide='Use Settings', source=None)
        self.assertEqual(self.knowledge.load('org.example.app', 'ios')['status'], 'unavailable')

    def test_draft_write_failure_is_reported_without_losing_the_observed_guide(self):
        with patch('app_knowledge.atomic', side_effect=OSError('private path')):
            self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        proposal = self.session.result['appKnowledgeProposal']
        self.assertEqual(proposal['status'], 'not-saved')
        self.assertIn('<redacted>', proposal['guide'])
        self.assertNotIn('private path', proposal['error'])
        self.repository.publish.assert_not_called()

    def test_missing_guide_does_not_claim_an_error(self):
        self.assertEqual(self.knowledge.load('org.example.app', 'android')['status'], 'none')

    def test_invalid_identity_cannot_escape_the_knowledge_directory(self):
        for app, platform in [('../other', 'ios'), ('org.example', '../other'), ('', 'ios')]:
            with self.subTest(app=app, platform=platform):
                self.assertEqual(self.knowledge.load(app, platform)['status'], 'unavailable')
        self.repository.read.assert_not_called()

    def test_proposal_retains_observation_provenance_without_device_identity(self):
        self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        proposal = self.session.result['appKnowledgeProposal']
        document = json.loads((self.root / proposal['artifact']).read_text())
        self.assertEqual(document['source'], dict(runId='run-1', appCommit='abc123', target='Debug', observedStepCount=2))
        self.assertNotIn('private-value', json.dumps(document))
        self.assertNotIn(self.device['id'], json.dumps(document))
        self.assertEqual((self.root / proposal['artifact']).stat().st_mode & 0o777, 0o600)

    def test_unchanged_or_absent_guide_creates_no_proposal(self):
        original = self.session.learned_app_knowledge
        for guide in [None, '', original]:
            self.session.application_knowledge['guide'] = original
            self.session.learned_app_knowledge = guide
            self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        self.assertEqual(self.knowledge.publish()['status'], 'nothing-new')
        self.repository.publish.assert_not_called()

    def test_interruption_keeps_the_draft_and_does_not_publish(self):
        self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        self.assertEqual(self.knowledge.publish(interrupted=True)['status'], 'not-published')
        self.assertTrue((self.root / self.session.result['appKnowledgeProposal']['artifact']).is_file())
        self.repository.publish.assert_not_called()

    def test_prepare_failure_keeps_proposals_without_publishing(self):
        self.repository.prepare.side_effect = InfrastructureError('Shared branch unavailable')
        self.knowledge.prepare()
        self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        self.assertEqual(self.knowledge.publish()['error'], 'Shared branch unavailable')
        self.repository.publish.assert_not_called()

    def test_device_drafts_are_retained_and_latest_snapshot_is_proposed(self):
        self.knowledge.stage(self.session, self.device, {'target': 'Debug'})
        self.session.learned_app_knowledge = 'Updated guide after another observation'
        self.knowledge.stage(self.session, dict(platform='ios', id='second-device'), {'target': 'Debug'})
        self.knowledge.publish()
        changes, run_id = self.repository.publish.call_args.args
        self.assertEqual(run_id, 'run-1')
        self.assertEqual(changes['knowledge/apps/ios/org.example.app.json']['guide'], self.session.learned_app_knowledge)
        self.assertEqual(len(list(self.root.rglob('*.json'))), 2)
