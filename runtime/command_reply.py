"""Read an explicit command and keep the complete AI reply as source data."""

import json
from errors import InfrastructureError


def read_reply(response):
    """A reply without one readable command remains a note for the next turn."""
    if response.get('status') != 'completed':
        raise InfrastructureError('OpenAI response was incomplete; no action executed')
    parts = [part for item in response.get('output', []) if item.get('type') == 'message'
             for part in item.get('content', [])]
    if any(part.get('type') == 'refusal' for part in parts):
        raise InfrastructureError('OpenAI refused the request; no action executed')
    text = ''.join(part.get('text', '') for part in parts if part.get('type') == 'output_text')
    try:
        value = json.loads(text)
    except ValueError:
        value = {}
    action = command(value if isinstance(value, dict) else {})
    action['modelResponse'] = text
    if action['action'] == 'note':
        action['observation'] = text
        action['resourceFeedback'] = 'No single executable command was supplied. No device action was dispatched.'
    return action


def command(value):
    """Fill omitted resource arguments. Do not score or approve the AI's content."""
    defaults = dict(action='note', ref='', text='', x=-1, y=-1, direction='', credential='',
        field='', observation='', repeatInstruction='', repeatReason='', remaining=[],
        completion='continue', checks=[], planUpdates=[], discoveredControls=[],
        configuration=[], pathDecisions=[], planStepId=0, context=None,
        recovery=dict(id=-1, decision='none', reason=''))
    result = dict(defaults)
    for name, default in defaults.items():
        supplied = value.get(name, default)
        if default is None or type(supplied) is type(default):
            result[name] = supplied
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
