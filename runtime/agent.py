"""Default OpenAI decision engine for CIMT's replaceable agent contract."""

import json
from copy import deepcopy
from ai_instructions.instructions import ActionPromptBuilder
from ai_services import AiServices
from command_reply import read_reply


class Agent:
    """Select actions; device execution and independent reviews are elsewhere."""

    def __init__(self, config, budget, deadline, transport=None, prompts=None):
        self.model = config["ai-model"]["name"]
        self.services = AiServices(config, budget, deadline, transport=transport)
        self.prompts = prompts or ActionPromptBuilder(self.model)

    def check_access(self):
        """Check that the configured decision model is available."""
        self.services.check_access()

    def decide(self, request):
        """Produce a decision through the replaceable agent contract."""
        return self.choose(*request.arguments(), observer=request.request_observer,
                           check_cancelled=request.check_cancelled, report_timing=request.report_timing)

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
        resource_feedback=None,
        exploration_memory=None,
        *, observer=None, check_cancelled=None, report_timing=None,
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
            resource_feedback,
            exploration_memory,
        )
        retry_body = deepcopy(body)
        state = json.loads(body['input'][-1]['content'][0]['text'])
        kind = ('context selection' if 'contextSelectionRequired' in state else
            'recovery' if 'recoveryRequest' in state['explorationMemory'] else 'decision')
        response = self.services.send(body, kind, observer, check_cancelled=check_cancelled,
                                      report_timing=report_timing)
        details = response.get('incomplete_details')
        if response.get('status') == 'incomplete' and isinstance(details, dict) and details.get('reason') == 'max_output_tokens':
            retry_body['input'][-1]['content'].append(dict(type='input_text', text=(
                'The previous response reached the output limit; none of its commands ran. '
                'Return a shorter response with only the next necessary commands and concise progress.')))
            response = self.services.send(retry_body, 'decision retry', observer,
                                          check_cancelled=check_cancelled, report_timing=report_timing)
        return read_reply(response)
