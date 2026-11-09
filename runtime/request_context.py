"""Request a smaller AI selection when its selected record payload is too large."""

import json

# This is a transport size allowance, not a relevance score or a history window.
MAX_SELECTED_CONTEXT_BYTES = 64 * 1024


def prepare_context(state, allowance=MAX_SELECTED_CONTEXT_BYTES):
    memory = state['explorationMemory']
    selected = {key: state[key] for key in ['recentActions', 'requirementResults', 'coverage']}
    selected['memory'] = memory
    size = len(json.dumps(selected, ensure_ascii=False).encode('utf-8'))
    if size <= allowance:
        return state
    # Defer the whole selected payload. The AI chooses which records to request next.
    state = dict(state, recentActions=[], requirementResults=[], coverage=[])
    state['explorationMemory'] = {key: memory[key] for key in [
        'summary', 'selection', 'catalogue', 'recoveryRequest'] if key in memory}
    state['contextSelectionRequired'] = dict(selectedBytes=size, allowanceBytes=allowance,
        reason='Selected record payload exceeds the request allowance. Return recall with your revised context selection.')
    return state
