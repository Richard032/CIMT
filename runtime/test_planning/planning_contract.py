"""The bounded planning fields in each single-action response."""

from errors import InvalidAgentResponse
from .context_memory import SELECTION_SCHEMA


def text(*choices):
    return dict(type='string', **({'enum': list(choices)} if choices else {}))


ROWS = {
    'planUpdates': dict(id={'type': 'integer'}, source=text('instructions', 'requirements'),
        requirementId=text(), instructionQuote=text(), subject=text(), expected=text(),
        status=text('pending', 'active', 'blocked'), reason=text(), targetState=text()),
    'discoveredControls': dict(ref=text(), kind=text('tap', 'text', 'toggle', 'select', 'scroll')),
    'configuration': dict(ref=text(), name=text(), value=text()),
    'pathDecisions': dict(id=text(), scope=text('in scope', 'out of scope', 'blocked'),
        reason=text(), planStepId={'type': 'integer'}),
}
LIMITS = dict(planUpdates=6, discoveredControls=20, configuration=8, pathDecisions=20)
FIELDS = {name: dict(type='array', maxItems=LIMITS[name], items=dict(
    type='object', properties=fields, required=list(fields), additionalProperties=False))
    for name, fields in ROWS.items()}
FIELDS['planStepId'] = {'type': 'integer'}
FIELDS['context'] = SELECTION_SCHEMA
FIELDS['recovery'] = dict(type='object', properties={
    'id': {'type': 'integer'}, 'decision': text('none', 'replan', 'intentional', 'blocked'),
    'reason': text()}, required=['id', 'decision', 'reason'], additionalProperties=False)


def validate_planning(action):
    if action['planStepId'] < 0:
        raise InvalidAgentResponse('planStepId must be a nonnegative task ID')
    recovery = action.get('recovery')
    if not isinstance(recovery, dict) or set(recovery) != {'id', 'decision', 'reason'}:
        raise InvalidAgentResponse('recovery needs id, decision and reason')
    if type(recovery['id']) is not int or recovery['decision'] not in ['none', 'replan', 'intentional', 'blocked'] or not isinstance(recovery['reason'], str):
        raise InvalidAgentResponse('Invalid recovery decision')
    if recovery['decision'] != 'none' and not recovery['reason'].strip():
        raise InvalidAgentResponse('A recovery decision needs an explanation')
    for name, fields in ROWS.items():
        if len(action[name]) > LIMITS[name]:
            raise InvalidAgentResponse('Too many ' + name + ' updates in one decision')
        for row in action[name]:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise InvalidAgentResponse('Invalid fields in ' + name)
            for key, schema in fields.items():
                expected = int if schema['type'] == 'integer' else str
                if type(row[key]) is not expected or ('enum' in schema and row[key] not in schema['enum']):
                    raise InvalidAgentResponse('Invalid ' + name + '.' + key)
                if expected is int and row[key] < 0:
                    raise InvalidAgentResponse('Negative ID in ' + name)
