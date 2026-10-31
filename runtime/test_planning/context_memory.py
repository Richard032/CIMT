"""Apply AI context selections without ranking or discarding source records."""

from copy import deepcopy
import re

COLLECTIONS = ['actions', 'decisions', 'observations', 'screenshots', 'tasks', 'paths', 'states', 'transitions', 'requirements', 'checks', 'configuration', 'coverage', 'routes']
SELECTION_SCHEMA = {
    'type': ['object', 'null'],
    'properties': {
        'summary': {'type': 'string'},
        'includeAll': {'type': 'array', 'items': {'type': 'string', 'enum': COLLECTIONS}},
        'records': {'type': 'array', 'items': {
            'type': 'object', 'properties': {
                'collection': {'type': 'string', 'enum': COLLECTIONS}, 'id': {'type': 'string'}},
            'required': ['collection', 'id'], 'additionalProperties': False}},
    },
    'required': ['summary', 'includeAll', 'records'], 'additionalProperties': False,
}


class ContextMemory:
    """The AI selects content. The host only resolves its exact record addresses."""

    def __init__(self):
        # At bootstrap there is no AI selection and no host relevance policy to apply.
        self.selection = None
        self.unavailable = []


    def accept(self, selection):
        # Null is an explicit AI request to keep its existing summary and selection.
        if selection is None:
            return
        self.selection = deepcopy(selection)

    def project(self, collections):
        """Return all records at bootstrap, then only the records requested by AI."""
        self.unavailable = []
        if self.selection is None:
            return deepcopy(collections)
        selected = {name: [] for name in COLLECTIONS}
        for name in self.selection['includeAll']:
            if name not in collections:
                self.unavailable.append('Collection not available: ' + name)
                continue
            selected[name] = deepcopy(collections[name])
        for address in self.selection['records']:
            name = address['collection']
            if name not in collections:
                self.unavailable.append('Collection not available: ' + name)
                continue
            rows = collections[name]
            index = self.index(rows)
            identifier = address['id']
            span = self.span(identifier)
            if span is not None:
                requested = rows[span[0]:span[1]] if 0 <= span[0] <= span[1] <= len(rows) else []
            else:
                row = rows[-1] if identifier == 'latest' and rows else index.get(identifier)
                requested = [row] if row is not None else []
            if not requested:
                self.unavailable.append('Resource not available: ' + name + '/' + identifier)
            for row in requested:
                if row not in selected[name]:
                    selected[name].append(deepcopy(row))
        return selected

    @staticmethod
    def index(rows):
        result = {str(row.get('id', number)): row for number, row in enumerate(rows)}
        result.update({'@' + str(number): row for number, row in enumerate(rows)})
        return result

    @staticmethod
    def span(identifier):
        match = re.fullmatch(r'@(\d+):(\d+)', identifier)
        return (int(match[1]), int(match[2])) if match else None

    def saved(self):
        return deepcopy(self.selection)
