"""Prepare instructions from source inputs and retained scenario information."""

import json


class InstructionContext:
    """Provides AI inputs. It never reads replies or dispatches app actions."""

    def __init__(self, inputs, credential_aliases, redactor):
        self.inputs = dict(inputs)
        self.credential_aliases = list(credential_aliases)
        self.redactor = redactor

    def prepare(self, session, device, evidence):
        """Use the AI's context selection without choosing relevant history for it."""
        screenshots = list(evidence.images.values())
        session.result['screenshots'] = screenshots
        memory = session.planner.context(session.elements, session.history,
            session.result['requirements'], session.result.get('checks', []),
            session.result.get('decisions', []), session.coverage.snapshot(), screenshots, session.commands.records, session.feedback.collection())
        if session.recovery.pending is not None:
            memory['recoveryRequest'] = self.redactor.records.recovery(session.recovery.pending)
        memory['batchFeedback'] = session.feedback.pending()
        memory['currentWarnings'] = [session.feedback.warnings[key] for key in session.feedback.current_warnings]
        memory = self.redactor.records.request_context(memory)
        # Historical pixels are supplied only when the AI selected them.
        memory['historicalImages'] = (evidence.load_images(memory['selectedScreenshots'])
            if session.planner.context_memory.selection is not None else [])
        return [self.inputs['instructions'], self.inputs.get('requirements', ''),
            self._setup(session, device), session.elements, session.image, session.history,
            self.credential_aliases, session.coverage.snapshot(), session.result['requirements'],
            session.resource_feedback, memory]

    def observe(self, mobile, session, evidence=None):
        """Ask the device adapter for fresh masked UI information and keep it."""
        session.elements, session.image = mobile.snapshot()
        session.planner.observe(session.elements)
        session.result.update(self.redactor.records.planning(session.planner.saved()))
        session.coverage.observe(session.elements)
        session.result['coverage'] = session.coverage.snapshot()
        if evidence is not None:
            name = 'observation-' + str(len(evidence.images)).zfill(4)
            references = evidence.save_step(name, session.elements, session.image)
            if session.observer:
                session.observer.record(session, references, len(session.result['steps']) - 1)
            session.result['screenshots'] = list(evidence.images.values())

    def _setup(self, session, device):
        """Keep one device's task separate from independently scheduled devices."""
        scope = dict(platform=device.get('platform', ''), deviceId=device.get('id', ''),
            target=session.result['target'])
        return self.inputs.get('setup', '') + '\nCIMT execution scope: ' + json.dumps(scope) + (
            '\nExecute the supplied objective only for this device and target. '
            'Report remaining work only within this scope. Other devices and targets '
            'are scheduled independently; do not claim they were or were not tested.')
