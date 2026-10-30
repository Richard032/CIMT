"""Coordinates cost reservation, API access, and action parsing."""

from action_prompt import ActionPromptBuilder, parse_action
from budget import Budget
from errors import InfrastructureError, LimitReached
from openai_transport import OpenAiTransport


class Agent:
    """Selects one action. It has no device or shell access."""

    def __init__(self, config, budget, deadline, transport=None, prompts=None):
        self.model = config["ai-model"]["name"]
        self.budget = budget
        self.transport = transport or OpenAiTransport(config["ai-model"]["api-key"], deadline)
        self.prompts = prompts or ActionPromptBuilder(self.model)

    def check_access(self):
        """Check model access without issuing an inference request."""
        self.transport.request("models/" + self.model)

    def choose(
        self,
        instructions,
        requirements,
        setup,
        elements,
        screenshot,
        history,
        aliases,
        coverage,
        requirement_results=None,
        correction_feedback=None,
        exploration_memory=None,
    ):
        """Request one action after the shared budget has reserved its maximum cost."""
        body = self.prompts.build(
            instructions,
            requirements,
            setup,
            elements,
            screenshot,
            history,
            aliases,
            coverage,
            requirement_results,
            correction_feedback,
            exploration_memory,
        )
        return parse_action(self._request_action(body))

    def _request_action(self, body):
        # Reserve before the request. Keep the full bound if usage is unknown.
        self.budget.reserve()
        response = None
        try:
            response = self.transport.request("responses", body)
            return response
        finally:
            usage = response.get("usage") if isinstance(response, dict) else None
            self.budget.finish(usage)
