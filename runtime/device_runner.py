"""Execution and fault handling for one physical device."""

import pathlib
from errors import InfrastructureError, LimitReached


class DeviceRunner:
    """Runs compatible targets in sequence on one device."""

    def __init__(
        self, context, redactor, control, journal, scenarios, mobile_factory, agent_factory
    ):
        self.context = context
        self.redactor = redactor
        self.control = control
        self.journal = journal
        self.scenarios = scenarios
        self.mobile_factory = mobile_factory
        self.agent_factory = agent_factory

    def run(self, device, index):
        """Test one startup device and publish its final state even after an error."""
        folder = pathlib.Path(self.context["report"]) / "devices" / ("device-" + str(index))
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        result = {
            "index": index,
            "device": self.redactor.records.device(device),
            "scenarios": [],
            "error": None,
            "stoppingReason": None,
        }
        self.journal.publish(result)
        mobile = self.mobile_factory(device, folder)
        try:
            mobile.connect()
            self._run_targets(mobile, result)
        except LimitReached as error:
            self._record_limit(result, error)
        except Exception as error:
            self._record_error(result, error)
        finally:
            mobile.close()
            self.journal.publish(result)

    def _run_targets(self, mobile, result):
        agent = self.agent_factory()
        for build in self.context["builds"]:
            if build["platform"] == mobile.device["platform"]:
                self.scenarios.run(
                    mobile, build, result, agent, lambda: self.journal.publish(result)
                )

    def _record_limit(self, result, error):
        result["stoppingReason"] = str(error)
        # A locked phone affects that device. Shared limits affect every worker.
        if "locked" not in str(error):
            self.control.stop()

    def _record_error(self, result, error):
        message = (
            str(error)
            if isinstance(error, InfrastructureError)
            else type(error).__name__ + ": " + str(error)
        )
        result["error"] = self.redactor.text(message)
        self.control.stop()


def result_exit_code(results):
    """Apply exit precedence to saved results, without any device operations."""
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
