"""Errors shared by the runtime services."""


class LimitReached(Exception):
    """The run cannot continue within its allowed time, budget, or device state."""


class InfrastructureError(Exception):
    """A required tool, response, or safety check did not work."""
