"""Execution and fault handling for one physical or virtual device."""

import pathlib
from contextlib import nullcontext
from errors import InfrastructureError, LimitReached
from stopping_policy.policy import stops_entire_run


class DeviceRunner:
    """Runs compatible targets in sequence on one device."""

    def __init__(
        self, context, redactor, control, journal, scenarios, mobile_factory, agent_factory,
        activity=None,
    ):
        self.context = context
        self.redactor = redactor
        self.control = control
        self.journal = journal
        self.scenarios = scenarios
        self.mobile_factory = mobile_factory
        self.agent_factory = agent_factory
        self.activity = activity

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
        with self._operation("Prepare device adapter", device):
            mobile = self.mobile_factory(device, folder)
        try:
            with self._operation("Connect device", device):
                mobile.connect()
            self._run_targets(mobile, result)
        except Exception as error:
            self._record_exception(result, error)
        finally:
            self._close(mobile, result)

    def _close(self, mobile, result):
        """Save the latest observations even when the adapter cannot close cleanly."""
        try:
            with self._operation("Close device connection", mobile.device):
                mobile.close()
        except Exception as error:
            self._record_exception(result, error)
        finally:
            self.journal.publish(result)

    def _record_exception(self, result, error):
        if self.control.interrupted:
            self._record_limit(result, LimitReached("User interrupted execution; partial observations were retained"))
        elif isinstance(error, LimitReached):
            self._record_limit(result, error)
        else:
            self._record_error(result, error)

    def _run_targets(self, mobile, result):
        agent = self.agent_factory()
        for build in self.context["builds"]:
            if build["platform"] == mobile.device["platform"]:
                with self._operation("Execute target", mobile.device, build["target"]):
                    self.scenarios.run(
                        mobile, build, result, agent, lambda: self.journal.publish(result)
                    )

    def _operation(self, name, device, target=""):
        return self.activity.operation(name, device, target) if self.activity else nullcontext()

    def _stop_event(self, result, error):
        if self.activity:
            target = result["scenarios"][-1]["target"] if result["scenarios"] else ""
            self.activity.write("Device stopped", self.activity.stop_status(error), str(error),
                result["device"], target, error=error,
                log="devices/device-" + str(result["index"]) + "/adapter.log")

    def _record_limit(self, result, error):
        result["stoppingReason"] = str(error)
        self._stop_event(result, error)
        if stops_entire_run(error):
            self.control.stop()

    def _record_error(self, result, error):
        message = (
            str(error)
            if isinstance(error, InfrastructureError)
            else type(error).__name__ + ": " + str(error)
        )
        # A later cleanup error must not replace the failure that stopped testing.
        if not result["error"]:
            result["error"] = self.redactor.text(message)
        self._stop_event(result, error)
        if stops_entire_run(error):
            self.control.stop()
