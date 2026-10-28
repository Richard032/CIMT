"""Composition root for the Python worker used by the public .NET command."""

import json
import pathlib
import sys
from actions import ActionExecutor
from agent import Agent
from budget import Budget
from device_runner import DeviceRunner, result_exit_code
from errors import InfrastructureError, LimitReached
from evidence import RunJournal
from mobile import Mobile
from redaction import Redactor
from run_control import RunControl
from scenario import ScenarioRunner
from device_scheduler import DeviceScheduler


class Execution:
    """Connects runtime services and schedules at most two device workers."""

    def __init__(self, context, mobile_factory=None, agent_factory=None, scheduler=None):
        self.context = context
        self.config = context["config"]
        self.redactor = Redactor(self.config)
        self.budget = Budget(
            self.config["ai-model"]["name"],
            self.config["ai-budget"]["amount"],
            self.config["ai-budget"]["currency"],
        )
        self.control = RunControl(context["deadline"])
        self.journal = RunJournal(
            context["report"], self.redactor, self.budget, context.get("runId", "")
        )
        self.budget.journal = self.journal.journal_budget
        self.journal.journal_budget()
        self.mobile_factory = mobile_factory or self._mobile
        self.agent_factory = agent_factory or self._agent
        self.scheduler = scheduler or DeviceScheduler()

    def run(self, preflight=False):
        """Check access or schedule the startup devices with at most two active."""
        if preflight:
            self.agent_factory().check_access()
            print(
                "Model access and local runtime/pricing checks passed. No inference request made."
            )
            return 0
        pathlib.Path(self.context["report"], "devices").mkdir(exist_ok=True)
        worker = self._device_runner()
        self.scheduler.run(self.context["devices"], worker)
        self.journal.save()
        return result_exit_code(self.journal.results)

    def _device_runner(self):
        actions = ActionExecutor(self.config, self.redactor, self.context["deadline"])
        scenarios = ScenarioRunner(
            self.context["inputs"],
            self.config,
            self.redactor,
            self.control,
            actions,
            self.context["report"],
            requirements=self.context.get("requirements", []),
        )
        return DeviceRunner(
            self.context,
            self.redactor,
            self.control,
            self.journal,
            scenarios,
            self.mobile_factory,
            self.agent_factory,
        )

    def _mobile(self, device, folder):
        return Mobile(self.context["nativeBinary"], device, folder, self.context, self.redactor)

    def _agent(self):
        return Agent(self.config, self.budget, self.context["deadline"])


def main(stream, arguments):
    """Read the private request from stdin and return a documented exit code."""
    try:
        context = json.load(stream)
        return Execution(context).run(preflight="--preflight" in arguments)
    except (InfrastructureError, LimitReached) as error:
        print("CIMT execution stopped: " + str(error), file=sys.stderr)
        return 3 if isinstance(error, InfrastructureError) else 2
    except Exception as error:
        print("CIMT execution infrastructure failed: " + type(error).__name__, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.stdin, sys.argv[1:]))
