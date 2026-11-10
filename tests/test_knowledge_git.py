"""Git isolation and PR protocol tests use local repositories and mocked HTTP."""

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from errors import InfrastructureError
from knowledge_git import KnowledgeGit, RejectRedirects


class KnowledgeGitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test Author')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.root / 'existing.txt').write_text('original')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.publisher = KnowledgeGit(dict(repository=str(self.root), remote='origin', baseBranch='feature/shared'), time.time() + 30)
        self.publisher.base = self.git('rev-parse', 'HEAD')
        self.publisher.github = 'example/CIMT'
        self.changes = {'knowledge/apps/ios/org.example.app.json': {'schemaVersion': 1, 'guide': 'Use Settings'}}

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def test_commit_preserves_head_staged_and_unstaged_work(self):
        (self.root / 'existing.txt').write_text('staged work')
        self.git('add', 'existing.txt')
        (self.root / 'existing.txt').write_text('unstaged work')
        status, staged = self.git('status', '--porcelain'), self.git('diff', '--cached')
        commit = self.publisher.commit(self.changes)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.publisher.base)
        self.assertEqual(self.git('status', '--porcelain'), status)
        self.assertEqual(self.git('diff', '--cached'), staged)
        self.assertEqual((self.root / 'existing.txt').read_text(), 'unstaged work')
        self.assertEqual(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', commit), next(iter(self.changes)))
        self.assertEqual(self.git('show', commit + ':existing.txt'), 'original')

    def test_read_reuses_only_the_selected_shared_commit(self):
        reviewed = self.publisher.commit(self.changes)
        path = self.root / next(iter(self.changes))
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'guide': 'Unreviewed local edit'}))
        self.assertIsNone(self.publisher.read(next(iter(self.changes))))
        self.publisher.base = reviewed
        self.assertEqual(self.publisher.read(next(iter(self.changes)))['guide'], 'Use Settings')
        self.assertEqual(json.loads(path.read_text())['guide'], 'Unreviewed local edit')

    def test_git_error_does_not_expose_stderr_with_credentials(self):
        self.publisher.run_command = Mock(return_value=subprocess.CompletedProcess([], 1, '', 'synthetic-token'))
        with self.assertRaisesRegex(InfrastructureError, '^Knowledge Git operation failed: push$'):
            self.publisher._git('-c', 'push.recurseSubmodules=no', 'push')

    def test_push_failure_cannot_claim_a_pushed_branch_or_pr(self):
        with patch.object(self.publisher, 'token', return_value='synthetic-token'), \
             patch.object(self.publisher, 'commit', return_value='abc123'), \
             patch.object(self.publisher, '_git', side_effect=InfrastructureError('Push failed')), \
             patch.object(self.publisher, '_create_pr') as pr:
            result = self.publisher.publish(self.changes, 'run-1')
        self.assertEqual(result['status'], 'not-published')
        pr.assert_not_called()

    def test_commit_cannot_include_unrelated_paths(self):
        with self.assertRaisesRegex(InfrastructureError, 'only application guide files'):
            self.publisher.commit({'README.md': {'guide': 'unexpected'}})

    def test_identical_document_has_no_new_commit(self):
        self.publisher.base = self.publisher.commit(self.changes)
        self.assertIsNone(self.publisher.commit(self.changes))

    def test_supported_remotes_resolve_the_same_repository(self):
        for remote in ['https://github.com/example/CIMT.git', 'git@github.com:example/CIMT.git', 'ssh://git@github.com/example/CIMT']:
            self.assertEqual(KnowledgeGit.github_name(remote), 'example/CIMT')

    def test_credentials_and_other_hosts_are_rejected(self):
        for remote in ['https://token@github.com/example/CIMT', 'https://github.com.evil.invalid/example/CIMT', 'https://example.invalid/repo']:
            with self.subTest(remote=remote), self.assertRaises(InfrastructureError):
                KnowledgeGit.github_name(remote)

    def test_missing_authentication_does_not_commit_or_push(self):
        with patch.object(self.publisher, 'token', return_value=None), patch.object(self.publisher, 'commit') as commit:
            result = self.publisher.publish(self.changes, 'run-1')
        self.assertEqual(result['status'], 'not-published')
        commit.assert_not_called()

    def test_push_uses_a_separate_branch_and_does_not_put_token_in_arguments(self):
        with patch.object(self.publisher, 'token', return_value='synthetic-token'), \
             patch.object(self.publisher, 'commit', return_value='abc123'), \
             patch.object(self.publisher, '_git') as git, \
             patch.object(self.publisher, '_create_pr', return_value='https://github.com/example/CIMT/pull/7'):
            result = self.publisher.publish(self.changes, 'run-1')
        self.assertEqual(result['status'], 'pr-created')
        args = git.call_args.args
        self.assertIn('abc123:refs/heads/' + result['branch'], args)
        self.assertIn('--force-with-lease=refs/heads/' + result['branch'] + ':', args)
        self.assertNotIn('synthetic-token', str(args))
        self.assertEqual(result['baseBranch'], 'feature/shared')

    def test_pr_failure_reports_the_pushed_branch_for_recovery(self):
        with patch.object(self.publisher, 'token', return_value='synthetic-token'), \
             patch.object(self.publisher, 'commit', return_value='abc123'), patch.object(self.publisher, '_git'), \
             patch.object(self.publisher, '_create_pr', side_effect=InfrastructureError('HTTP 403')):
            result = self.publisher.publish(self.changes, 'run-1')
        self.assertEqual(result['status'], 'branch-pushed')
        self.assertEqual(result['commit'], 'abc123')
        self.assertEqual(result['error'], 'HTTP 403')

    def test_api_creates_only_a_pr_against_the_configured_branch(self):
        http = Mock()
        http.open.return_value = io.BytesIO(b'{"html_url":"https://github.com/example/CIMT/pull/7"}')
        self.publisher.http = http
        url = self.publisher._create_pr('synthetic-token', 'knowledge/new', self.changes, 'run-1')
        request = http.open.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.full_url, 'https://api.github.com/repos/example/CIMT/pulls')
        self.assertEqual(request.get_header('X-github-api-version'), '2026-03-10')
        self.assertEqual((body['base'], body['head']), ('feature/shared', 'knowledge/new'))
        self.assertNotIn('merge', body)
        self.assertEqual(url, 'https://github.com/example/CIMT/pull/7')

    def test_http_failure_does_not_expose_the_response_body(self):
        http = Mock()
        http.open.side_effect = urllib.error.HTTPError('url', 403, 'private response', {}, io.BytesIO(b'private body'))
        self.publisher.http = http
        with self.assertRaisesRegex(InfrastructureError, '^Knowledge PR creation failed with HTTP 403$'):
            self.publisher._create_pr('synthetic-token', 'knowledge/new', self.changes, 'run-1')

    def test_redirects_are_not_followed_with_credentials(self):
        with self.assertRaises(InfrastructureError):
            RejectRedirects().redirect_request(None, None, None, None, None, None)

    def test_interruption_before_pr_creation_keeps_the_pushed_branch(self):
        http = Mock()
        self.publisher.http = http
        self.publisher.interrupted = lambda: True
        with patch.object(self.publisher, 'token', return_value='synthetic-token'), \
             patch.object(self.publisher, 'commit', return_value='abc123'), patch.object(self.publisher, '_git'):
            result = self.publisher.publish(self.changes, 'run-1')
        self.assertEqual(result['status'], 'branch-pushed')
        self.assertIn('interrupted', result['error'])
        http.open.assert_not_called()

    def test_deadline_prevents_git_operations(self):
        self.publisher.deadline = time.time() - 1
        with self.assertRaisesRegex(InfrastructureError, 'deadline'):
            self.publisher.commit(self.changes)
