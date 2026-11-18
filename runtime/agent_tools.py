"""Map registered SDK tools to CIMT commands and report observed results."""

import json
import math
import re

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

REQUIRED_ARGUMENTS = {
    'credential': ('credential', 'field', 'ref'),
    'demo_swipe': ('direction', 'distance'),
    'swipe': ('direction',),
    'text': ('text',),
}

ARGUMENT_TYPES = {
    'array': (list,),
    'integer': (int,),
    'null': (type(None),),
    'number': (int, float),
    'object': (dict,),
    'string': (str,),
}

COMMAND_METADATA = (
    'observation', 'progressNote', 'planStepId', 'planUpdates', 'checks',
    'discoveredControls', 'configuration', 'pathDecisions', 'context', 'recovery',
    'remaining', 'repeatInstruction', 'repeatReason',
)


def register_tools(platform):
    """Publish tools supported on the device, using existing command argument schemas."""
    return [
        dict(type='function', name=name, description=description, strict=False,
             parameters=dict(type='object', additionalProperties=False,
                 required=['observation', *REQUIRED_ARGUMENTS.get(name, ())],
                 properties={key: tool_property(key) for key in (*arguments.split(), *COMMAND_METADATA)}))
        for name, (description, arguments) in TOOLS.items()
        if platform == 'android' or name not in ('back', 'sample_memory')
    ]


def tool_property(key):
    """Keep detailed nested metadata definitions in the shared command resources."""
    field = FIELDS[key]
    if key == 'context':
        return dict(type=['object', 'null'], properties={}, additionalProperties=True,
                    description='Use summary, includeAll, and records from commandResources.toolContextExample.')
    if key == 'checks' or (field.get('type') == 'array' and 'properties' in field['items']):
        return dict(type='array', items=dict(type='object', properties={}, additionalProperties=True),
                    description=f'Use the {key} fields in commandResources.arguments.')
    return field


def argument_error(name, values, parameters):
    """Reject malformed arguments before command defaults can change their meaning."""
    if not isinstance(values, dict):
        return 'Supply the tool arguments as a JSON object.'
    properties = parameters['properties']
    if values.keys() - properties.keys():
        return 'Use only arguments declared by the tool.'
    for key in parameters['required']:
        if key not in values:
            return f'Missing required tool argument: {key}.'
    for key, value in values.items():
        if error := schema_error(value, FIELDS[key]):
            return f'Tool argument {key} {error}.'
    if name in ('tap', 'demo_tap'):
        ref = bool(values.get('ref'))
        x, y = (values.get(axis, -1) != -1 for axis in ('x', 'y'))
        if (ref and (x or y)) or (not ref and not (x and y)):
            return 'Supply either a target ref or both x and y coordinates.'
    return ''


def schema_error(value, field):
    if 'anyOf' in field:
        return ('does not match a declared form'
                if all(schema_error(value, choice) for choice in field['anyOf']) else '')
    types = field['type'] if isinstance(field['type'], list) else [field['type']]
    if not any(type(value) in ARGUMENT_TYPES[kind] for kind in types):
        return 'must be ' + ' or '.join(types)
    if type(value) is float and not math.isfinite(value):
        return 'must be finite'
    if 'enum' in field and value not in field['enum']:
        return 'is outside the declared choices'
    if value is not None and 'minimum' in field and value < field['minimum']:
        return f'must be at least {field["minimum"]}'
    if 'pattern' in field and not re.search(field['pattern'], value):
        return 'does not match the required format'
    if isinstance(value, dict):
        for key in field.get('required', []):
            if key not in value:
                return f'is missing {key}'
        properties = field['properties']
        if value.keys() - properties.keys():
            return 'contains undeclared fields'
        for key, item in value.items():
            if error := schema_error(item, properties[key]):
                return f'property {key} {error}'
    if isinstance(value, list):
        for index, item in enumerate(value):
            if error := schema_error(item, field['items']):
                return f'item {index} {error}'
    return ''


def original_tool_call(call):
    """Keep the raw argument text available to the report's secret redactor."""
    header = {key: value for key, value in call.items() if key != 'arguments'}
    arguments = call.get('arguments')
    if not isinstance(arguments, str):
        return json.dumps(call, ensure_ascii=False)
    return json.dumps(header, ensure_ascii=False) + '\n' + arguments


class ToolTurn:
    """Accept one SDK tool call and return its normalized command to the runner."""

    def __init__(self, definitions):
        self.definitions = {definition['name']: definition for definition in definitions}
        self.call = None
        self.reply = None
        self.reasoning = []
        self.original_calls = []

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
        self.original_calls = calls
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
        error = argument_error(name, values, parameters)
        if error:
            self.reject(error)
            return 'Invalid tool arguments. No device command accepted.'
        self.reply = command(dict(values, action=name))
        self.reply['modelResponse'] = original_tool_call(self.original_calls[0])
        self.reply['toolCall'] = dict(self.call, reasoning=self.reasoning)
        return 'Command accepted for CIMT dispatch.'

    def reject(self, reason):
        self.reply = command({})
        self.reply['resourceFeedback'] = reason + ' No device action was dispatched.'
        self.reply['modelResponse'] = '\n\n'.join(original_tool_call(call) for call in self.original_calls)


def tool_exchange(previous_tool_result):
    """Encode the last observed command result as a Responses API tool result."""
    if previous_tool_result is None:
        return []
    call, result = previous_tool_result
    return [*call['reasoning'],
            dict(type='function_call', name=call['name'], call_id=call['call_id'], arguments=call['arguments']),
            dict(type='function_call_output', call_id=call['call_id'],
                 output=json.dumps(result, ensure_ascii=False))]
