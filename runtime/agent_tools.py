"""Map registered SDK tools to CIMT commands and report observed results."""

import json

from agents import FunctionTool
from openai.types.responses import ResponseFunctionToolCall

from ai_instructions.instructions import FIELDS
from command_reply import command


TOOLS = {
    'tap': ('Tap a current control ref or absolute screen coordinates.', 'ref x y'),
    'swipe': ('Swipe in the specified finger direction.', 'ref x y direction distance durationMs'),
    'demo_tap': ('Preview a tap without sending input.', 'ref x y expectedRef'),
    'demo_swipe': ('Preview a swipe without sending input.', 'ref x y direction distance durationMs expectedRef'),
    'show_gesture': ('Inspect a recorded gesture preview.', 'gestureCommandId'),
    'text': ('Type synthetic text into the focused control.', 'text'),
    'credential': ('Replace the contents of a field using a configured credential alias.', 'credential field ref'),
    'back': ('Press the Android system Back button.', ''),
    'wait': ('Wait while respecting the shared run deadline.', 'durationMs'),
    'restart': ('Restart the tested application.', ''),
    'sample_memory': ('Sample PSS and RSS of the tested Android application.', ''),
}


def register_tools(platform):
    """Publish tools supported on the device, using existing command argument schemas."""
    return [
        dict(type='function', name=name, description=description, strict=False,
             parameters=dict(type='object', additionalProperties=False, required=['observation'],
                 properties={key: FIELDS[key] for key in (*arguments.split(), 'observation', 'progressNote')}))
        for name, (description, arguments) in TOOLS.items()
        if platform == 'android' or name not in ('back', 'sample_memory')
    ]


class ToolTurn:
    """Accept one SDK tool call and return its normalized command to the runner."""

    def __init__(self, definitions):
        self.definitions = {definition['name']: definition for definition in definitions}
        self.call = None
        self.reply = None
        self.reasoning = []

    def sdk_tools(self):
        return [FunctionTool(name=tool['name'], description=tool['description'],
                    params_json_schema=tool['parameters'], strict_json_schema=tool['strict'],
                    on_invoke_tool=self.invoke)
                for tool in self.definitions.values()]

    def output(self, response):
        calls = [item for item in response.get('output', []) if item.get('type') == 'function_call']
        if not calls or response.get('status') != 'completed':
            return []
        if any(part.get('type') == 'refusal' for item in response['output']
               if item.get('type') == 'message' for part in item.get('content', [])):
            return []
        if len(calls) == 1:
            call = calls[0]
            name = call.get('name')
            if (isinstance(name, str) and name in self.definitions
                    and isinstance(call.get('call_id'), str) and call['call_id']
                    and isinstance(call.get('arguments'), str)):
                self.call = {key: call[key] for key in ('name', 'call_id', 'arguments')}
                self.reasoning = [item for item in response['output'] if item.get('type') == 'reasoning'
                                  and item.get('encrypted_content')]
                return [ResponseFunctionToolCall(type='function_call', **self.call)]
        self.reject('Call one registered tool per decision.')
        return []

    async def invoke(self, context, arguments):
        try:
            values = json.loads(arguments)
        except ValueError:
            values = None
        name = self.call['name']
        parameters = self.definitions[name]['parameters']
        if (not isinstance(values, dict) or set(values) - parameters['properties'].keys()
                or not isinstance(values.get('observation'), str)):
            self.reject('Supply the arguments declared by the registered tool, including observation.')
            return 'Invalid tool arguments. No device command accepted.'
        self.reply = command(dict(values, action=name))
        self.reply['modelResponse'] = json.dumps(dict(type='function_call', **self.call), ensure_ascii=False)
        self.reply['toolCall'] = dict(self.call, reasoning=self.reasoning)
        return 'Command accepted for CIMT dispatch.'

    def reject(self, reason):
        self.reply = command({})
        self.reply['resourceFeedback'] = reason + ' No device action was dispatched.'


def tool_exchange(previous_tool_result):
    """Encode the last observed command result as a Responses API tool result."""
    if previous_tool_result is None:
        return []
    call, result = previous_tool_result
    return [*call['reasoning'],
            dict(type='function_call', name=call['name'], call_id=call['call_id'], arguments=call['arguments']),
            dict(type='function_call_output', call_id=call['call_id'],
                 output=json.dumps(result, ensure_ascii=False))]
