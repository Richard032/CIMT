"""Contracts for independent completion review and proposal generation."""

from dataclasses import dataclass
from typing import Callable, Literal, Protocol, TypedDict


class RequestObserver(Protocol):
    def begin(self, body: dict, kind: str) -> dict: ...
    def finish(self, record: dict, status: str, usage: dict | None = None) -> None: ...


@dataclass(frozen=True)
class EvidenceRequest:
    """Redacted evidence and recording for one advisory request."""

    evidence: dict
    request_observer: RequestObserver | None = None
    check_cancelled: Callable[[], None] | None = None


class CompletionReview(TypedDict):
    decision: Literal['agree', 'revise']
    feedback: str


class ProposalResult(TypedDict):
    interpretation: str
    instructions: str
    setup: str
    evidence: str


class CompletionReviewer(Protocol):
    def review(self, request: EvidenceRequest) -> CompletionReview: ...


class ProposalGenerator(Protocol):
    def propose(self, request: EvidenceRequest) -> ProposalResult: ...
