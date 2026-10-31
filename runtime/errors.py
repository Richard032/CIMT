"""Errors shared by the runtime services."""


class LimitReached(Exception):
    """The run cannot continue within its allowed time, budget, or device state."""


class InfrastructureError(Exception):
    """A required tool, response, or safety check did not work."""


class InvalidAgentResponse(InfrastructureError):
    """An AI response can be corrected before any device action is accepted."""

    def __init__(self, message, response=None):
        super().__init__(message)
        # This stays in memory until the report boundary removes known secrets.
        self.response = response


class CaptureChanged(InfrastructureError):
    """The screen changed between the checks around one screenshot."""


class NoProgressAction(Exception):
    """A repetition signal needs AI assessment before another app action."""
