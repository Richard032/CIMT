"""Save a reviewable proposal without changing the source inputs."""

from pathlib import Path


class InstructionProposal:
    """Use recorded, redacted run evidence to draft setup and instructions."""

    def __init__(self, report, inputs, results, redactor, control, agent, activity):
        self.path = Path(report) / "instruction-setup-proposal.md"
        self.inputs = inputs
        self.results = results
        self.redactor = redactor
        self.control = control
        self.agent = agent
        self.activity = activity

    def create(self):
        """Save either a proposal or an explicit reason it could not be generated."""
        try:
            self.control.check()
            if not self.results:
                raise ValueError("No device results are available")
            evidence = self.redactor.object({"inputs": self.inputs, "devices": self.results})
            proposal = self.redactor.object(self.agent.propose(evidence))
            text = ("# Instruction and setup proposal\n\n"
                    "Draft for review. Original inputs remain unchanged.\n\n"
                    "## Proposed instructions\n\n" + proposal["instructions"] +
                    "\n\n## Proposed setup\n\n" + proposal["setup"] +
                    "\n\n## Supporting evidence and uncertainty\n\n" + proposal["evidence"] + "\n")
            self.path.write_text(text, encoding="utf-8")
            self.activity.write("Instruction proposal", "completed", "Review instruction-setup-proposal.md before using it.")
        except Exception as error:
            # A proposal failure must not change the already recorded test result.
            self.path.write_text("# Instruction and setup proposal\n\n"
                "No AI proposal was generated. Reason: " + self.redactor.text(str(error)) + "\n", encoding="utf-8")
            self.activity.write("Instruction proposal", "failed", "Proposal unavailable; see instruction-setup-proposal.md.")
