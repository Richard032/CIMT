"""Remember observed application states and verified navigation routes."""

from collections import deque
from .screen_model import app_elements, control_identity, identity, progress_identity, screen_label, view_identity
from errors import InvalidAgentResponse


class ApplicationMap:
    def __init__(self):
        self.states = {}
        self.transitions = []
        self.configuration = {}

    def state_id(self, elements):
        values = {name: row['value'] for name, row in self.configuration.items()}
        return identity([progress_identity(elements), values])

    def observe(self, elements):
        state = self.state_id(elements)
        self.states.setdefault(state, {
            'id': state, 'screen': view_identity(elements),
            'label': screen_label(elements),
            'configuration': {name: dict(row) for name, row in self.configuration.items()},
        })
        return state

    def validate_configuration(self, updates, elements):
        current = {item.get('ref'): item for item in app_elements(elements)}
        if len({row['name'] for row in updates}) != len(updates) or len({row['ref'] for row in updates}) != len(updates):
            raise InvalidAgentResponse('Configuration observations must use unique names and refs')
        for row in updates:
            element = current.get(row['ref'])
            if not element or not row['name'].strip() or not row['value'].strip():
                raise InvalidAgentResponse('Configuration observations need a current ref, name and visible value')
            values = [str(element.get(key, '')) for key in ['text', 'label', 'value']]
            values += [str(element[key]).lower() for key in ['checked', 'selected'] if key in element]
            if row['value'] not in values or '<masked>' in row['value'] or '<redacted>' in row['value']:
                raise InvalidAgentResponse('Configuration value must match the referenced current element')
            control = control_identity(element)
            if any(name != row['name'] and old['control'] == control for name, old in self.configuration.items()):
                raise InvalidAgentResponse('Use the existing configuration name for this observed control')

    def configure(self, updates, elements):
        source = self.observe(elements)
        current = {item.get('ref'): item for item in elements}
        for row in updates:
            self.configuration[row['name']] = dict(value=row['value'],
                control=control_identity(current[row['ref']]), observedAt=source)
        self.observe(elements)

    def record(self, before, after, control, action, outcome, verified, routable=None):
        source, destination = self.observe(before), self.observe(after)
        self.transitions.append(dict(source=source, destination=destination, control=control,
            action=action, outcome=outcome, verified=verified,
            routable=verified if routable is None else routable))

    def route(self, source, destination):
        """Use only observed successful transitions. A proposed route is not executed blindly."""
        pending = deque([(source, [])])
        visited = {source}
        while pending:
            state, route = pending.popleft()
            if state == destination:
                return route
            for edge in self.transitions:
                if edge['source'] == state and edge['routable'] and edge['destination'] not in visited:
                    visited.add(edge['destination'])
                    pending.append((edge['destination'], route + [dict(edge)]))
        return []

    def saved(self):
        return dict(states=list(self.states.values()), transitions=self.transitions,
                    configuration=self.configuration)
