"""Contract between TestPilot execution and a replaceable decision agent."""

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class KnowledgeLookup(Protocol):
    """Search the current app's approved entries or retrieve one by ID."""

    def __call__(self, *, query: str = "", entry_id: str = "") -> list | dict | None:
        ...


@dataclass(frozen=True)
class DecisionRequest:
    """A fresh observation and task context for one decision."""

    instructions: str
    requirements: str
    setup: str
    elements: list
    screenshot: bytes
    history: list
    credential_aliases: list
    coverage: dict
    requirement_results: Any = None
    resource_feedback: Any = None
    exploration_memory: Any = None
    request_observer: Any = None
    report_timing: Callable[[dict], None] | None = None
    budget: Any = None
    deadline: float | None = None
    check_cancelled: Callable[[], None] | None = None
    previous_tool_result: tuple[dict, dict] | None = None
    knowledge_lookup: KnowledgeLookup | None = None

    def arguments(self):
        """Return the values used by the existing OpenAI prompt builder."""
        return (self.instructions, self.requirements, self.setup, self.elements,
                self.screenshot, self.history, self.credential_aliases, self.coverage,
                self.requirement_results, self.resource_feedback, self.exploration_memory)


class DecisionAgent(Protocol):
    """Choose TestPilot commands without owning the device or the scenario lifecycle."""

    def check_access(self) -> None:
        """Check agent readiness without performing a test decision."""
        ...

    def decide(self, request: DecisionRequest) -> dict:
        """Return normalized TestPilot commands for the observed context."""
        ...
