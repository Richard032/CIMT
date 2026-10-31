"""Redact record text while keeping its control fields unchanged."""

from errors import InfrastructureError
import re


class RecordRedactor:
    """Each record type declares its metadata and its nested record types."""

    def __init__(self, redactor):
        self.redactor = redactor

    def check(self, value):
        keep = ["id", "taskId", "step", "screenshot"]
        if value.get('source') in ['instructions', 'requirements']:
            keep.append('source')
        if value.get('status') in ['passed', 'failed', 'not tested', 'inconclusive', 'overridden']:
            keep.append('status')
        if re.fullmatch(r'REQ-\d+', value.get('requirementId', '')) or not value.get('requirementId'):
            keep.append('requirementId')
        return self._record(value, keep)

    def requirement(self, value):
        return self._record(value, ["id", "status", "startLine", "endLine", "step", "screenshot"])

    def action(self, value):
        if isinstance(value, str):
            # String actions are host step names, such as check or reset/install/launch.
            return value
        return self._record(
            value,
            ["action", "ref", "direction", "credential", "field", "completion", "planStepId"],
            {"checks": lambda items: self._items(items, self.check),
             'context': self.context, 'recovery': self.recovery},
        )

    def step(self, value):
        return self._record(value, ["step", "screenshot", "ui", "planStepId", "sourceState", "destinationState"], {"action": self.action})

    def crash(self, value):
        return self._record(
            value,
            ["step", "matchingAttempt"],
            {"reproductionSteps": lambda items: self._items(items, self.action)},
        )

    def scenario(self, value):
        return self._record(
            value,
            ["target", "appId", "verdict", "completion"],
            {
                "steps": lambda items: self._items(items, self.step),
                "checks": lambda items: self._items(items, self.check),
                "requirements": lambda items: self._items(items, self.requirement),
                "crashes": lambda items: self._items(items, self.crash),
                "rejectedResponses": lambda items: self._items(items, self.rejected_response),
                "testPlan": self.plan,
                "exploration": self.exploration,
                'recoveries': lambda items: self._items(items, self.recovery),
                'contextSelection': self.context,
                'decisions': lambda rows: self._items(rows, self.decision),
                'screenshots': lambda rows: self._items(rows, self.screenshot),
            },
        )

    def rejected_response(self, value):
        # The candidate response is untrusted data, including its source and ID fields.
        return self._record(value, ["attempt", "step", "status", "screenshot"])

    def plan(self, value):
        return self._record(value, ['activeTaskId', 'nextTaskId'], {
            'tasks': lambda rows: self._items(rows, self.task)})

    def task(self, value):
        keep = ['id', 'targetState']
        if value.get('source') in ['instructions', 'requirements']:
            keep.append('source')
        if re.fullmatch(r'REQ-\d+', value.get('requirementId', '')) or not value.get('requirementId'):
            keep.append('requirementId')
        for name in ['status', 'result']:
            if value.get(name) in ['pending', 'active', 'blocked', 'tested', 'passed', 'failed',
                                   'not tested', 'inconclusive', 'overridden']:
                keep.append(name)
        return self._record(value, keep)

    def planning(self, value):
        return self._record(value, [], {'testPlan': self.plan, 'exploration': self.exploration,
                                      'contextSelection': self.context})

    def context(self, value):
        if value is None:
            return None
        return self._record(value, [], {
            'includeAll': lambda rows: list(rows),
            'records': lambda rows: self._items(rows, lambda row: self._record(row, ['collection', 'id']))})

    def request_context(self, value):
        path = lambda row: self._record(row, ['id', 'screen', 'control', 'action', 'kind', 'scope', 'planStepId', 'ref'])
        return self._record(value, ['currentScreen'], {
            'testPlan': self.plan,
            'selection': self.context,
            'currentControls': lambda rows: self._items(rows, path),
            'paths': lambda rows: self._items(rows, path),
            'applicationMap': lambda row: self._record(row, [], {
                'states': lambda rows: self._items(rows, lambda item: self._record(item, ['id', 'screen'],
                    {'configuration': self._configuration, 'observations': lambda ids: list(ids)})),
                'transitions': lambda rows: self._items(rows, lambda item: self._record(item,
                    ['source', 'destination', 'control', 'action', 'destinationObservation'])),
                'configuration': lambda rows: self._items(rows, lambda item: self._record(item, ['id', 'control', 'observedAt'])),
            }),
            'selectedActions': lambda rows: self._items(rows, self.action),
            'selectedRequirements': lambda rows: self._items(rows, self.requirement),
            'selectedChecks': lambda rows: self._items(rows, self.check),
            'selectedDecisions': lambda rows: self._items(rows, self.decision),
            'selectedObservations': lambda rows: self._items(rows, self.observation),
            'selectedScreenshots': lambda rows: self._items(rows, self.screenshot),
            'routes': lambda rows: self._items(rows, lambda row: self._record(row, ['id', 'destination'], {
                'edges': lambda edges: self._items(edges, lambda edge: self._record(edge, ['source', 'destination', 'control', 'action']))})),
            'recoveryRequest': self.recovery,
        })

    def recovery(self, value):
        return self._record(value, ['id', 'step', 'kind', 'status', 'decision'], {'proposal': self.action})

    def decision(self, value):
        return self._record(value, ['id', 'step'], {'response': self.action})

    def observation(self, value):
        return self._record(value, ['id', 'state'], {'elements': lambda rows: self._items(rows, self.element)})

    def screenshot(self, value):
        return self._record(value, ['id', 'path', 'sha256'])

    def exploration(self, value):
        return self._record(value, [], {
            'paths': lambda rows: self._items(rows, lambda row: self._record(row,
                ['id', 'screen', 'control', 'action', 'kind', 'scope', 'planStepId'])),
            'transitions': lambda rows: self._items(rows, lambda row: self._record(row, ['source', 'destination'])),
            'applicationMap': self._map,
        })

    def _configuration(self, value):
        return {self.redactor.text(name): self._record(row, ['control', 'observedAt']) for name, row in value.items()}

    def _map(self, value):
        return self._record(value, [], {
            'states': lambda rows: self._items(rows, lambda row: self._record(row, ['id', 'screen'],
                {'configuration': self._configuration, 'observations': lambda ids: list(ids)})),
            'transitions': lambda rows: self._items(rows, lambda row: self._record(row,
                ['source', 'destination', 'control', 'action', 'destinationObservation'])),
            'configuration': self._configuration,
            'refinements': lambda rows: dict(rows),
            'observations': lambda rows: self._items(rows, self.observation),
        })

    def device(self, value):
        return self._record(value, ["id", "platform", "type"])

    def element(self, value):
        return self._record(value, ["ref", "type", "enabled"])

    def device_result(self, value):
        return self._record(
            value,
            ["index"],
            {"device": self.device, "scenarios": lambda items: self._items(items, self.scenario)},
        )

    def _record(self, value, metadata, children=None):
        if not isinstance(value, dict):
            raise InfrastructureError("A result record must be an object")
        children = children or {}
        result = {}
        for key, item in value.items():
            if key in children:
                result[key] = children[key](item)
            elif key in metadata:
                if isinstance(item, (dict, list)):
                    raise InfrastructureError("A result metadata field must be a scalar")
                result[key] = item
            else:
                # Unknown fields are text data too. A field name alone grants no exemption.
                result[key] = self.redactor.object(item)
        return result

    @staticmethod
    def _items(values, convert):
        if not isinstance(values, list):
            raise InfrastructureError("A result collection must be a list")
        return [convert(value) for value in values]
