"""Execution Stopping Policy: stopping scope, crash limit and final exit precedence.

This layer makes no device, file, model or timing calls. Execution services enforce
its decisions and keep the evidence that explains why testing stopped.
"""

from errors import AppLaunchError, DeviceLocked


def stops_entire_run(error):
    """A rejected app launch or locked device does not stop other devices."""
    return not isinstance(error, (AppLaunchError, DeviceLocked))


def matching_crash_limit_reached(attempts):
    """Three crashes at the same point stop only the affected scenario."""
    return attempts >= 3


def result_exit_code(results):
    """Preserve failures even when another device finishes successfully."""
    if any(device["error"] for device in results):
        return 3
    if any(
        scenario["crashes"] or scenario.get("verdict") == "failed"
        for device in results
        for scenario in device["scenarios"]
    ):
        return 1
    if not results or any(_incomplete(device) for device in results):
        return 2
    return 0


def _incomplete(device):
    return (
        device["stoppingReason"]
        or not device["scenarios"]
        or any(
            scenario["completion"] != "complete" or scenario.get("verdict") != "passed"
            for scenario in device["scenarios"]
        )
    )
