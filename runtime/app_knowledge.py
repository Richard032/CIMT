"""Retain AI-authored app guides separately from issue instructions and test results."""

from copy import deepcopy
import hashlib
from pathlib import Path
import re
import threading
from evidence import atomic
from errors import InfrastructureError
from knowledge_git import KnowledgeGit


class AppKnowledge:
    """Loads reviewed Git guides and retains per-run proposals for one publication PR."""

    def __init__(self, settings, context, redactor, repository=None, interrupted=None):
        self.context = context
        self.redactor = redactor
        self.repository = repository or KnowledgeGit(settings, context['deadline'], interrupted=interrupted)
        self.pending = {}
        self.lock = threading.Lock()
        self.error = None

    def prepare(self):
        try:
            self.repository.prepare()
        except InfrastructureError as error:
            self.error = str(error)

    @staticmethod
    def path(app_id, platform):
        if platform not in ['ios', 'android'] or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', app_id):
            raise InfrastructureError('App knowledge requires a valid verified app ID and platform')
        return 'knowledge/apps/' + platform + '/' + app_id + '.json'

    def load(self, app_id, platform):
        result = dict(enabled=True, appId=app_id, platform=platform, status='none', guide='')
        try:
            if self.error:
                raise InfrastructureError(self.error)
            document = self.repository.read(self.path(app_id, platform))
            if document is not None:
                if (not isinstance(document, dict) or document.get('schemaVersion') != 1
                    or document.get('appId') != app_id or document.get('platform') != platform
                    or not isinstance(document.get('guide'), str)):
                    raise InfrastructureError('Shared app knowledge identity or format is invalid')
                source = document.get('source', {})
                if not isinstance(source, dict) or any(isinstance(value, (dict, list)) for value in source.values()):
                    raise InfrastructureError('Shared app knowledge provenance is invalid')
                result.update(status='loaded', guide=document['guide'],
                    source={key: value for key, value in source.items()
                            if key in ['runId', 'appCommit', 'target', 'observedStepCount']})
        except InfrastructureError as error:
            result.update(status='unavailable', error=str(error))
        result['guide'] = self.redactor.text(result['guide'])
        return result

    def stage(self, session, device, build):
        guide = session.learned_app_knowledge
        if not guide or guide == session.application_knowledge.get('guide'):
            return
        path = self.path(session.app_id, device['platform'])
        document = dict(schemaVersion=1, appId=session.app_id,
            platform=device['platform'], guide=self.redactor.text(guide),
            source=dict(runId=self.context.get('runId', ''), appCommit=self.context.get('sourceCommit', ''),
                        target=build['target'], observedStepCount=len(session.result['steps'])))
        identity = hashlib.sha256((device['id'] + '\n' + build['target']).encode()).hexdigest()[:12]
        artifact = 'app-knowledge-proposals/' + device['platform'] + '/' + session.app_id + '-' + identity + '.json'
        destination = Path(self.context['report']) / artifact
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic(destination, document)
            destination.chmod(0o600)
        except OSError:
            self.error = 'Application knowledge proposal could not be saved'
            session.result['appKnowledgeProposal'] = dict(document, status='not-saved', error=self.error)
            return
        session.result['appKnowledgeProposal'] = dict(document, artifact=artifact)
        with self.lock:
            self.pending[path] = document

    def publish(self, interrupted=False):
        with self.lock:
            pending = deepcopy(self.pending)
        if not pending:
            return dict(status='nothing-new')
        if interrupted:
            return dict(status='not-published', error='Run interrupted; learned proposals remain in the report')
        if self.error:
            return dict(status='not-published', error=self.error)
        return self.repository.publish(pending, self.context['runId'])
