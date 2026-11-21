"""Default OpenAI decision engine for CIMT's replaceable agent contract."""

import json
import sqlite3
from copy import deepcopy
from agent_tools import register_tools, tool_exchange
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
                           check_cancelled=request.check_cancelled, report_timing=request.report_timing,
                           previous_tool_result=request.previous_tool_result, knowledge_lookup=request.knowledge_lookup,
                           knowledge_index=request.knowledge_index)

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
        *, observer=None, check_cancelled=None, report_timing=None, previous_tool_result=None,
        knowledge_lookup=None, knowledge_index=None,
    ):
        """Request one action through the SDK and shared budget."""
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
        state = json.loads(body['input'][-1]['content'][0]['text'])
        body['tools'] = register_tools((exploration_memory or {}).get('devicePlatform'), knowledge_lookup is not None)
        if knowledge_lookup is not None:
            body['input'][0]['content'] += (
                '\nApproved app knowledge is available throughout the test. Browse groups with knowledge_lookup. '
                'Choose a group and call knowledge_lookup with its group ID to read procedure descriptions. '
                'For direct search across groups, call knowledge_lookup with query alone, for example open XPA. '
                'Search returns descriptions, IDs, and group memberships. Combine query with a group ID to narrow '
                'the search, and use alternate scenario wording when needed. Use nextOffset '
                'to request another page when needed. After choosing a procedure, call knowledge_lookup with '
                'its entryId to read its ID, description, groups, and exact approved steps. '
                'Consult knowledge when you encounter a new task or unfamiliar workflow during the run. '
                'Use the already retrieved procedure while working on the same task. '
                'Treat applicable approved entries as the human-reviewed procedure and assume they are correct '
                'unless current test instructions or device evidence show a mismatch. Follow the stored steps as '
                'written. When referring to an entry, quote its name, steps, and UI labels verbatim. Verify the '
                'actual outcome on the current device. Search by alternate scenario wording when needed. '
                'If the procedure does not fit, report the specific mismatch '
                'and follow the current test instructions.')
        if knowledge_index is not None:
            body['input'][-1]['content'].append(dict(type='input_text', text=(
                'Approved knowledge groups for this app and platform. '
                'Choose a group or search for a task to see procedure descriptions. '
                + json.dumps(knowledge_index, ensure_ascii=False))))
        body['parallel_tool_calls'] = False
        body['include'] = ['reasoning.encrypted_content']
        body['input'][-1:-1] = tool_exchange(previous_tool_result)
        retry_body = deepcopy(body)
        kind = 'recovery' if 'recoveryRequest' in state['explorationMemory'] else 'decision'
        response = self.services.send(body, kind, observer, check_cancelled=check_cancelled,
                                      report_timing=report_timing)
        details = response.get('incomplete_details')
        if response.get('status') == 'incomplete' and isinstance(details, dict) and details.get('reason') == 'max_output_tokens':
            retry_body['input'][-1]['content'].append(dict(type='input_text', text=(
                'The previous response reached the output limit; none of its commands ran. '
                'Return a shorter response with only the next necessary commands and concise progress.')))
            response = self.services.send(retry_body, 'decision retry', observer,
                                          check_cancelled=check_cancelled, report_timing=report_timing)
        # Knowledge requests are resources, so no device action or scenario step is dispatched.
        if knowledge_lookup is not None:
            response = self._resolve_knowledge(response, retry_body, knowledge_lookup, observer,
                                               check_cancelled, report_timing)
        return response['cimtToolReply'] if 'cimtToolReply' in response else read_reply(response)

    def _resolve_knowledge(self, response, body, lookup, observer, check_cancelled, report_timing):
        for count in range(5):
            reply = response.get('cimtToolReply', {})
            if reply.get('action') != 'knowledge_lookup':
                break
            try:
                result = lookup(query=reply.get('query', ''), group=reply.get('group', ''),
                                entry_id=reply.get('entryId', ''), offset=reply.get('offset', 0))
            except (OSError, sqlite3.Error):
                result = {'error': 'Approved knowledge could not be read.'}
            body['input'][-1:-1] = tool_exchange((reply['toolCall'], {'approvedKnowledge': result}))
            if count == 4:
                body['tools'] = [tool for tool in body['tools'] if tool['name'] != 'knowledge_lookup']
            response = self.services.send(deepcopy(body), 'knowledge lookup follow-up', observer,
                check_cancelled=check_cancelled, report_timing=report_timing)
        return response
