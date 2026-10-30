"""Redact record text while keeping its control fields unchanged."""

from errors import InfrastructureError


class RecordRedactor:
    """Each record type declares its metadata and its nested record types."""

    def __init__(self, redactor):
        self.redactor = redactor

    def check(self, value):
        return self._record(value, ["source", "status", "requirementId", "step", "screenshot"])

    def requirement(self, value):
        return self._record(value, ["id", "status", "startLine", "endLine", "step", "screenshot"])

    def action(self, value):
        if isinstance(value, str):
            # String actions are host step names, such as check or reset/install/launch.
            return value
        return self._record(
            value,
            ["action", "ref", "direction", "credential", "field", "completion"],
            {"checks": lambda items: self._items(items, self.check)},
        )

    def step(self, value):
        return self._record(value, ["step", "screenshot", "ui"], {"action": self.action})

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
            },
        )

    def rejected_response(self, value):
        # The candidate response is untrusted data, including its source and ID fields.
        return self._record(value, ["attempt", "step", "status", "screenshot"])

    def device(self, value):
        return self._record(value, ["id", "platform"])

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
