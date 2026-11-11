"""Save a reviewable proposal without changing the source inputs."""

from pathlib import Path


class InstructionProposal:
    """Use recorded, redacted run evidence to draft setup and instructions."""

    def __init__(self, report, inputs, redactor, activity):
        self.path = Path(report) / "instruction-setup-proposal.md"
        self.inputs = redactor.object(inputs)
        self.redactor = redactor
        self.activity = activity

    def create(self, agent, results, outcome):
        evidence = self.redactor.object({"inputs": self.inputs, "runOutcome": outcome, "devices": results})
        proposal = self.redactor.object(agent.propose(evidence))
        self._write("AI draft for review.", proposal)
        self.activity.write("Instruction proposal", "completed", "Review instruction-setup-proposal.md before using it.")

    def unavailable(self, reason):
        self._write("No AI proposal was generated. Reason: " + self.redactor.text(reason), {
            "interpretation": "AI interpretation is unavailable. The original test instructions are included below.",
            "instructions": self.inputs.get("instructions") or "No testing instructions were loaded.",
            "setup": self.inputs.get("setup") or "No setup was supplied.",
            "evidence": "See the run report for any recorded results and stopping reasons.",
        })
        self.activity.write("Instruction proposal", "failed", "Proposal unavailable; see instruction-setup-proposal.md.")

    def _write(self, status, proposal):
        text = ("# Instruction and setup proposal\n\n" + status +
                "\n\n## Interpretation of the testing task\n\n" + proposal["interpretation"] +
                "\n\n## Proposed instructions\n\n" + proposal["instructions"] +
                "\n\n## Proposed setup\n\n" + proposal["setup"] +
                "\n\n## Supporting evidence and uncertainty\n\n" + proposal["evidence"] + "\n")
        temporary = self.path.with_suffix(".md.partial")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)
