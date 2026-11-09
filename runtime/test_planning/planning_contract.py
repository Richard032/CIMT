"""Describe optional planning resources without approving AI responses."""

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
FIELDS = {name: dict(type='array', items=dict(
    type='object', properties=fields, required=list(fields), additionalProperties=False))
    for name, fields in ROWS.items()}
FIELDS['planStepId'] = {'type': 'integer'}
FIELDS['context'] = SELECTION_SCHEMA
FIELDS['recovery'] = dict(type='object', properties={
    'id': {'type': 'integer'}, 'decision': text('none', 'replan', 'intentional', 'blocked'),
    'reason': text()}, required=['id', 'decision', 'reason'], additionalProperties=False)

