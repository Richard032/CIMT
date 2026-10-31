"""Coordinates cost reservation, API access, and action parsing."""

import json
from action_prompt import ActionPromptBuilder, parse_action
from openai_transport import OpenAiTransport
from errors import InvalidAgentResponse


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
        action = parse_action(self._request_action(body))
        state = json.loads(body['input'][1]['content'][0]['text'])
        can_stop = action['action'] == 'done' and action['completion'] == 'blocked' and action['remaining']
        if 'contextSelectionRequired' in state and action['action'] != 'recall' and not can_stop:
            raise InvalidAgentResponse('Context reduction is pending; return recall or explain blocked remaining work', action)
        return action

    def _request_action(self, body):
        state = json.loads(body['input'][1]['content'][0]['text'])
        kind = ('context selection' if 'contextSelectionRequired' in state else
            'recovery' if 'recoveryRequest' in state['explorationMemory'] else 'decision')
        # Keep cache-write charges within the rate used by this pricing profile.
        if self.budget.price.get("cache_ttl"):
            body["prompt_cache_options"] = {"ttl": self.budget.price["cache_ttl"], 'mode': 'explicit'}
            body['input'][0]['content'] = [dict(type='input_text', text=body['input'][0]['content'],
                prompt_cache_breakpoint={'mode': 'explicit'})]
        # Reserve before the request. Keep the full bound if usage is unknown.
        self.budget.reserve()
        response = None
        try:
            response = self.transport.request("responses", body)
            return response
        finally:
            usage = response.get("usage") if isinstance(response, dict) else None
            self.budget.finish(usage, kind=kind)
