"""Composition root for the Python worker used by the public .NET command."""

import json
import os
import pathlib
import shutil
import sys
import time
from actions import ActionExecutor
from agent import Agent
from ai_services import AiServices
from budget import Budget
from device_runner import DeviceRunner
from stopping_policy.policy import result_exit_code
from errors import InfrastructureError, LimitReached
from evidence import RunJournal, ScenarioEvidence, atomic
from request_journal import RequestJournal
from device_adapter.mobile import Mobile
from redaction import Redactor
from run_control import RunControl
from scenario import ScenarioRunner
from device_scheduler import DeviceScheduler
from activity import ActivityLog
from instruction_proposal import InstructionProposal
from run_signals import RunSignals
from runtime_protocol import read_request, read_results
from result_review.critic import CompletionCritic
from result_review.proposal import OpenAiProposal
from knowledge.store import KnowledgeStore
from knowledge.proposals import OpenAiKnowledgeProposal, write_proposals


class Execution:
    """Connects runtime services and schedules at most two device workers."""

    def __init__(self, context, mobile_factory=None, agent_factory=None, scheduler=None, review_factory=None, budget_factory=None):
        self.context = context
        self.config = context["config"]
        self.knowledge = (KnowledgeStore(os.environ["CIMT_INSTALL_ROOT"])
                          if context.get("learning") else None)
        self.redactor = Redactor(self.config)
        self.budget = (budget_factory or Budget)(
            self.config["ai-model"]["name"],
            self.config["ai-budget"]["amount"],
            self.config["ai-budget"]["currency"],
        )
        self.control = RunControl(context["deadline"], stop_file=pathlib.Path(context["report"]) / "stop-requested")
        self.activity = ActivityLog(context["report"], self.redactor,
                                   interrupted=lambda: self.control.interrupted)
        self.journal = RunJournal(
            context["report"], self.redactor, self.budget, context.get("runId", "")
        )
        self.budget.journal = self.journal.journal_budget
        self.journal.journal_budget()
        self.mobile_factory = mobile_factory or self._mobile
        self.agent_factory = agent_factory or self._agent
        self.review_factory = review_factory or self._reviewer
        self.scheduler = scheduler or DeviceScheduler()

    def run(self, preflight=False):
        """Check access or schedule the startup devices with at most two active."""
        if preflight:
            for tool in ("node", "mcp-server-mobile"):
                if shutil.which(tool) is None:
                    raise InfrastructureError(
                        "Required device adapter executable is missing from PATH: " + tool
                        + ". Repair the CIMT tool installation; its command paths are configured automatically."
                    )
            self.agent_factory().check_access()
            print(
                "Model access and local runtime/pricing checks passed for "
                + self.config["ai-model"]["name"] + ". No inference request made."
            )
            return 0
        pathlib.Path(self.context["report"], "devices").mkdir(exist_ok=True)
        worker = self._device_runner()
        self.scheduler.run(self.context["devices"], worker)
        self.journal.save()
        self.activity.write("Device test summary", "finished",
            "Exit " + str(result_exit_code(self.journal.results))
            + "; AI inference requests: " + str(self.budget.snapshot()["requests"]))
        return result_exit_code(self.journal.results)

    def _device_runner(self):
        actions = ActionExecutor(self.config, self.redactor, self.context["deadline"], check=self.control.check)
        scenarios = ScenarioRunner(
            self.context["inputs"],
            self.config,
            self.redactor,
            self.control,
            actions,
            self.context["report"],
            requirements=self.context.get("requirements", []),
            activity=self.activity, budget=self.budget, knowledge=self.knowledge,
        )
        return DeviceRunner(
            self.context,
            self.redactor,
            self.control,
            self.journal,
            scenarios,
            self.mobile_factory,
            self.agent_factory,
            activity=self.activity, reviewer_factory=self.review_factory,
        )

    def _mobile(self, device, folder):
        return Mobile(self.context["nativeBinary"], device, folder, self.context, self.redactor,
                      activity=self.activity, check=self.control.check)

    def _agent(self):
        return Agent(self.config, self.budget, self.context["deadline"])

    def _reviewer(self):
        return CompletionCritic(AiServices(self.config, self.budget, self.context["deadline"]))


def finalize_proposal(context, proposal_factory=None, budget_factory=None, knowledge_factory=None):
    """Review the saved run after device execution and its cancellation have ended."""
    config = context["config"]
    report = pathlib.Path(context["report"])
    redactor = Redactor(config)
    activity = ActivityLog(report, redactor)
    proposal = InstructionProposal(report, context["inputs"], redactor, activity)
    try:
        ledger = report / "ai-budget.json"
        budget = (budget_factory or Budget)(config["ai-model"]["name"], config["ai-budget"]["amount"], config["ai-budget"]["currency"])
        if ledger.exists():
            budget.restore(json.loads(ledger.read_text(encoding="utf-8")))
        budget.journal = lambda: atomic(ledger, budget.snapshot())
        outcome = context["outcome"]
        try:
            results = read_results(report / "ui-results.json")
        except InfrastructureError as error:
            results = []
            outcome = dict(outcome, deviceEvidenceUnavailable=str(error))
        request_folder = report / "proposal-requests"
        request_folder.mkdir(parents=True, exist_ok=True)
        request_result = {"steps": []}
        def request_deadline():
            return min(context["deadline"], time.time() + context.get("proposalRequestSeconds", 60))

        observer = RequestJournal(request_result, ScenarioEvidence(request_folder, report), redactor,
            lambda: atomic(report / "proposal-requests.json", redactor.object(request_result)))
        try:
            deadline = request_deadline()
            generator = (proposal_factory(config, budget, deadline) if proposal_factory
                         else OpenAiProposal(AiServices(config, budget, deadline)))
            proposal.create(generator, results, outcome, observer)
        except Exception as error:
            proposal.unavailable(str(error))
        if context.get("learning"):
            service = AiServices(config, budget, request_deadline()) if knowledge_factory is None else None
            knowledge = knowledge_factory() if knowledge_factory else OpenAiKnowledgeProposal(service)
            write_proposals(report, knowledge, observer, KnowledgeStore(os.environ["CIMT_INSTALL_ROOT"]),
                            redactor, context.get("builds", []),
                            {"inputs": context["inputs"], "runOutcome": outcome, "devices": results})
    except Exception as error:
        # Proposal failures cannot change the verdict or exit code of device testing.
        if not proposal.path.exists():
            proposal.unavailable(str(error))
        if context.get("learning"):
            atomic(report / "knowledge-proposals.json",
                   {"message": "Knowledge proposals unavailable: " + type(error).__name__, "requests": []})
    return 0


def main(stream, arguments):
    """Read the private request from stdin and return a documented exit code."""
    try:
        context = read_request(stream, proposal="--proposal" in arguments)
        if "--proposal" in arguments:
            return finalize_proposal(context)
        execution = Execution(context)
        preflight = "--preflight" in arguments
        with RunSignals(execution.control):
            return execution.run(preflight=preflight)
    except (InfrastructureError, LimitReached) as error:
        print("CIMT execution stopped: " + str(error), file=sys.stderr)
        return 3 if isinstance(error, InfrastructureError) else 2
    except Exception as error:
        print("CIMT execution infrastructure failed: " + type(error).__name__, file=sys.stderr)
        return 3


def wait_for_debugger(arguments):
    """Pause the selected worker entry point before reading the private request."""
    phase = "proposal" if "--proposal" in arguments else "preflight" if "--preflight" in arguments else "execution"
    if os.environ.get("CIMT_DEBUG_PYTHON") != phase:
        return
    sys.path.insert(0, os.environ["CIMT_DEBUGPY_PATH"])
    try:
        import debugpy
    finally:
        sys.path.pop(0)
    debugpy.configure(subProcess=False)
    debugpy.listen(("127.0.0.1", 5678))
    print(f"CIMT activity: Python {phase} worker waiting for the debugger on port 5678.", flush=True)
    debugpy.wait_for_client()


if __name__ == "__main__":
    wait_for_debugger(sys.argv[1:])
    raise SystemExit(main(sys.stdin, sys.argv[1:]))
