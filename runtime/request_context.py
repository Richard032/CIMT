"""Describe selected history size without choosing records for the AI."""

import json

MAX_SELECTED_CONTEXT_BYTES = 64 * 1024


def encoded_size(value):
    return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))


def context_usage(state, allowance=MAX_SELECTED_CONTEXT_BYTES):
    memory = state['explorationMemory']
    selected = {key: state[key] for key in ['recentActions', 'requirementResults', 'coverage']}
    selected['memory'] = memory
    collections = dict(actions=state['recentActions'], requirements=state['requirementResults'],
        coverage=state['coverage'])
    for name, key in [('batches', 'selectedBatches'), ('commands', 'selectedCommands'),
                      ('checks', 'selectedChecks'), ('decisions', 'selectedDecisions'),
                      ('observations', 'selectedObservations'), ('screenshots', 'selectedScreenshots'),
                      ('paths', 'paths'), ('routes', 'routes')]:
        collections[name] = memory.get(key, [])
    collections['tasks'] = memory.get('testPlan', {}).get('tasks', [])
    for name in ['states', 'transitions', 'configuration']:
        collections[name] = memory.get('applicationMap', {}).get(name, [])
    return dict(selectedBytes=encoded_size(selected), allowanceBytes=allowance,
        collections={name: dict(records=len(rows), bytes=encoded_size(rows))
                     for name, rows in collections.items()})


def prepare_context(state, allowance=MAX_SELECTED_CONTEXT_BYTES):
    usage = context_usage(state, allowance)
    state = dict(state, contextUsage=usage)
    if usage['selectedBytes'] <= allowance:
        return state
    memory = state['explorationMemory']
    # Defer the whole selected payload. The AI still owns the selection.
    state.update(recentActions=[], requirementResults=[], coverage=[])
    state['explorationMemory'] = {key: memory[key] for key in [
        'summary', 'selection', 'catalogue', 'recoveryRequest'] if key in memory}
    state['contextSelectionRequired'] = dict(usage,
        reason='Selected history exceeds the request allowance. Choose a smaller selection, '
               'continue from the supplied screen evidence, or explain a blocker. '
               'includeAll loads every record in each named collection; it does not mean latest. '
               'recall without context retains the previous selection.',
        exampleSelection=dict(summary='Your working summary', includeAll=[],
                              records=[dict(collection='observations', id='latest')]))
    return state
