"""Errors shared by the runtime services."""


class LimitReached(Exception):
    """The run cannot continue within its allowed time, budget, or device state."""


class DeviceLocked(LimitReached):
    """Only this device must wait for its user to unlock it."""


class InfrastructureError(Exception):
    """A required tool, response, or safety check did not work."""


class AppLaunchError(InfrastructureError):
    """The adapter answered, but could not launch this device's tested app."""


class DeviceActionError(InfrastructureError):
    """The adapter rejected an interaction; the AI decides what to try next."""


class CaptureChanged(InfrastructureError):
    """The screen changed between the checks around one screenshot."""


class NoProgressAction(Exception):
    """A repetition signal needs AI assessment before another app action."""
