"""Read ordered commands and keep the complete AI reply as source data."""

import json
import math
from errors import InfrastructureError


def read_reply(response):
    """Decode ordered commands; keep unreadable text as a note for the next turn."""
    if response.get('status') != 'completed':
        raise InfrastructureError('OpenAI response was incomplete; no action executed')
    parts = [part for item in response.get('output', []) if item.get('type') == 'message'
             for part in item.get('content', [])]
    if any(part.get('type') == 'refusal' for part in parts):
        raise InfrastructureError('OpenAI refused the request; no action executed')
    text = ''.join(part.get('text', '') for part in parts if part.get('type') == 'output_text')
    values, feedback = command_objects(text)
    commands = [command(value) for value in values]
    if feedback or not commands:
        note = command({})
        note.update(observation=text, resourceFeedback=feedback or
            command_feedback('No command objects were supplied.'))
        commands.append(note)
    first, *following = commands
    first['modelResponse'] = text
    if first['action'] == 'note' and not first.get('resourceFeedback'):
        first.update(observation=text, resourceFeedback=
            'No executable command was supplied in this object. No device action was dispatched for it.')
    if following:
        first['queuedCommands'] = following
    return first


def command_feedback(reason):
    """Describe the transport contract without judging the AI's testing decisions."""
    return (reason + ' No commands from this reply were executed. '
        'Expected one JSON command object, a JSON array containing only command objects, '
        'or consecutive JSON command objects with optional whitespace between them. '
        'For multiple commands, prefer an array, for example: '
        '[{"action":"wait"},{"action":"wait"}]. '
        'Use commandResources for supported actions and arguments. '
        'Correct the reply and resend the intended commands. The original reply was retained as a note.')


def command_objects(text):
    """Decode the complete reply before allowing any of its commands to execute."""
    remaining = text.lstrip()
    values = []
    decoder = json.JSONDecoder()
    while remaining:
        try:
            value, end = decoder.raw_decode(remaining)
        except json.JSONDecodeError as error:
            position = len(text) - len(remaining) + error.pos
            line = text.count('\n', 0, position) + 1
            column = position - text.rfind('\n', 0, position)
            reason = ('Unexpected comma between top-level commands; commas separate commands only inside an array'
                if remaining.startswith(',') else error.msg)
            return [], command_feedback(
                f'Invalid JSON command reply at line {line}, column {column}: {reason}.')
        objects = value if isinstance(value, list) else [value]
        if not all(isinstance(item, dict) for item in objects):
            return [], command_feedback(
                'Invalid command structure: every command must be a JSON object; scalar values and nested arrays are not commands.')
        values.extend(objects)
        remaining = remaining[end:].lstrip()
    return values, ''


def command(value):
    """Fill omitted resource arguments. Do not score or approve the AI's content."""
    defaults = dict(action='note', ref='', text='', x=-1, y=-1, direction='', distance=None, durationMs=None, credential='',
        field='', observation='', repeatInstruction='', repeatReason='', remaining=[],
        completion='continue', checks=[], planUpdates=[], discoveredControls=[],
        configuration=[], pathDecisions=[], planStepId=0, context=None, learnedAppKnowledge=None,
        recovery=dict(id=-1, decision='none', reason=''))
    result = dict(defaults)
    for name, default in defaults.items():
        supplied = value.get(name, default)
        if default is None or type(supplied) is type(default):
            result[name] = supplied
    if result['action'] == 'swipe':
        # Preserve numeric/invalid gesture arguments for execution feedback, never a centre fallback.
        for name in ['x', 'y', 'distance', 'durationMs']:
            supplied = value.get(name, defaults[name])
            # Invalid numbers/containers must still produce valid JSON failure reports.
            if isinstance(supplied, (dict, list)):
                supplied = json.dumps(supplied, ensure_ascii=False)
            elif type(supplied) is float and not math.isfinite(supplied):
                supplied = str(supplied)
            result[name] = supplied
        if 'ref' in value and not isinstance(value['ref'], str):
            result['argumentError'] = 'Swipe ref must be a string'
    result['remaining'] = [str(row) for row in result['remaining']]
    result['recovery'] = records([result['recovery']], defaults['recovery'])[0]
    result['checks'] = records(result['checks'], dict(taskId=-1, subject='', source='',
        status='inconclusive', expected='', observed='', reason='', requirementId='', instructionQuote=''))
    result['planUpdates'] = records(result['planUpdates'], dict(id=-1, source='instructions',
        requirementId='', instructionQuote='', subject='', expected='', status='pending', reason='', targetState=''))
    result['discoveredControls'] = records(result['discoveredControls'], dict(ref='', kind=''))
    result['configuration'] = records(result['configuration'], dict(ref='', name='', value=''))
    result['pathDecisions'] = records(result['pathDecisions'], dict(id='', scope='unclassified', reason='', planStepId=0))
    if result['context'] is not None:
        selection = result['context']
        if isinstance(selection, dict):
            result['context'] = dict(summary=str(selection.get('summary', '')),
                includeAll=[str(name) for name in selection.get('includeAll', [])]
                    if isinstance(selection.get('includeAll'), list) else [],
                records=records(selection.get('records', []), dict(collection='', id='')))
        else:
            result['context'] = None
    return result


def records(values, defaults):
    """Bind optional record arguments. The original reply is retained separately."""
    if not isinstance(values, list):
        return []
    rows = []
    for value in values:
        if not isinstance(value, dict):
            continue
        rows.append({name: value.get(name, default) if type(value.get(name, default)) is type(default)
                     else default for name, default in defaults.items()})
    return rows
