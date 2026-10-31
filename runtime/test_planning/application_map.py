"""Remember observed application states and verified navigation routes."""

from collections import deque
from copy import deepcopy
from .screen_model import app_elements, control_identity, identity, input_state, progress_identity, screen_label, view_identity
from errors import InvalidAgentResponse


class ApplicationMap:
    def __init__(self):
        self.states = {}
        self.transitions = []
        self.configuration = {}
        self.refinements = {}
        self.observations = {}

    def state_id(self, elements):
        values = {name: row['value'] for name, row in self.configuration.items()}
        return self.resolve(identity([view_identity(elements), input_state(elements), values]))

    def resolve(self, state):
        while state in self.refinements:
            state = self.refinements[state]
        return state

    def observe(self, elements):
        state = self.state_id(elements)
        self.states.setdefault(state, {
            'id': state, 'screen': view_identity(elements),
            'label': screen_label(elements),
            'configuration': {name: dict(row) for name, row in self.configuration.items()},
            'observations': [],
        })
        observation = identity(elements)
        self.observations.setdefault(observation, dict(id=observation, state=state, elements=deepcopy(elements)))
        if observation not in self.states[state]['observations']:
            self.states[state]['observations'].append(observation)
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
        changed_value = any(row['name'] in self.configuration
            and self.configuration[row['name']]['value'] != row['value'] for row in updates)
        current = {item.get('ref'): item for item in elements}
        for row in updates:
            self.configuration[row['name']] = dict(value=row['value'],
                control=control_identity(current[row['ref']]), observedAt=source)
        destination = self.observe(elements)
        if updates and source != destination:
            # Learning a value refines this observation; it is not an app navigation.
            if not changed_value:
                self.refinements[source] = destination
            elif self.transitions:
                edge = self.transitions[-1]
                if edge['destination'] == source and edge['destinationObservation'] == progress_identity(elements):
                    # Change only this arrival. Earlier visits may have used another value.
                    edge['destination'] = destination

    def record(self, before, after, control, action, outcome, verified, routable=None):
        source, destination = self.observe(before), self.observe(after)
        self.transitions.append(dict(source=source, destination=destination, control=control,
            action=action, outcome=outcome, verified=verified,
            destinationObservation=progress_identity(after),
            routable=verified if routable is None else routable))

    def route(self, source, destination):
        """Use only observed successful transitions. A proposed route is not executed blindly."""
        source, destination = self.resolve(source), self.resolve(destination)
        pending = deque([(source, [])])
        visited = {source}
        while pending:
            state, route = pending.popleft()
            if state == destination:
                return route
            for edge in self.transitions:
                start, end = self.resolve(edge['source']), self.resolve(edge['destination'])
                if start == state and edge['routable'] and end not in visited:
                    visited.add(end)
                    pending.append((end, route + [dict(edge, source=start, destination=end)]))
        return []

    def saved(self):
        return dict(states=list(self.states.values()), transitions=self.transitions,
                    configuration=self.configuration, refinements=dict(self.refinements),
                    observations=list(self.observations.values()))
