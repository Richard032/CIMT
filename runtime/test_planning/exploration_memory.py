"""Track attempted paths and their outcomes independently of recent AI history."""

from .application_map import ApplicationMap
from .screen_model import app_elements, control_identity, control_kind, identity, label, progress_identity, view_identity
from errors import InvalidAgentResponse, NoProgressAction


class ExplorationMemory:
    def __init__(self):
        self.paths = {}
        self.transitions = []
        self.plan = []
        self.map = ApplicationMap()
        self.identified = {}
        self.progress_version = 0

    def _key(self, elements, element, action):
        control = self._control(element, action)
        state = self.map.state_id(elements)
        direction = action.get('direction', '')
        for key, row in self.paths.items():
            if (self.map.resolve(row['screen']) == state and row['control'] == control
                    and row['action'] == action['action'] and row.get('direction', '') == direction):
                return key
        return identity([state, control, action['action'], direction])

    @staticmethod
    def _control(element, action):
        if element:
            return control_identity(element)
        # An unobserved target is a request, not a newly observed UI control.
        return identity([action['action'], action.get('ref', ''), action.get('x'),
                         action.get('y'), action.get('direction', '')])

    def _path(self, elements, action):
        element = next((item for item in elements if item.get('ref') == action.get('ref')), {})
        return self._key(elements, element, action)

    def kind(self, element):
        if element.get('enabled') is False or element.get('visible') is False:
            return ''
        return control_kind(element) or self.identified.get(control_identity(element), '')

    def observe(self, elements):
        state = self.map.state_id(elements)
        added = state not in self.map.states
        self.map.observe(elements)
        for element in app_elements(elements):
            kind = self.kind(element)
            if not kind:
                continue
            action = 'swipe' if kind == 'scroll' else 'tap'
            key = self._key(elements, element, {'action': action})
            if key not in self.paths:
                self.paths[key] = self._new_path(key, state, element, action, kind)
                added = True
        if added:
            self.progress_version += 1

    @staticmethod
    def _new_path(key, state, element, action, kind=''):
        return dict(id=key, screen=state, control=control_identity(element), label=label(element),
            action=action, kind=kind, attempts=0, unchangedAttempts=0, repeatedWithoutNewPath=0,
            scope='unclassified', reason='', planStepId=0)

    def validate_updates(self, action, elements, task_ids):
        current = {item.get('ref'): item for item in app_elements(elements)}
        if len({row['id'] for row in action['pathDecisions']}) != len(action['pathDecisions']):
            raise InvalidAgentResponse('Path scope updates contain duplicate IDs')
        for row in action['discoveredControls']:
            item = current.get(row['ref'])
            if not item or item.get('enabled') is False or item.get('visible') is False:
                raise InvalidAgentResponse('A discovered input needs a currently visible enabled ref')
        self.map.validate_configuration(action['configuration'], elements)
        for row in action['pathDecisions']:
            if row['id'] not in self.paths or row['planStepId'] not in task_ids or not row['reason'].strip():
                raise InvalidAgentResponse('Path decisions need a known path/task ID and a scope explanation')

    def update(self, action, elements):
        current = {item.get('ref'): item for item in elements}
        for row in action['discoveredControls']:
            self.identified[control_identity(current[row['ref']])] = row['kind']
        for row in action['pathDecisions']:
            self.paths[row['id']].update(scope=row['scope'], reason=row['reason'], planStepId=row['planStepId'])
        self.map.configure(action['configuration'], elements)
        self.observe(elements)

    def validate(self, elements, action, instructions):
        if action['action'] not in ['tap', 'swipe', 'back', 'text', 'credential', 'restart']:
            return
        path = self.paths.get(self._path(elements, action), {})
        repeated_cycle = (path.get('repeatedWithoutNewPath', 0) >= 3
                          and path.get('progressVersion') == self.progress_version)
        if path.get('unchangedAttempts', 0) < 3 and not repeated_cycle:
            return
        quote = action.get('repeatInstruction', '')
        if quote.strip() and quote in instructions and action.get('repeatReason', '').strip():
            return
        raise NoProgressAction('Repetition signal: this path repeated without a new discovered path. '
            'Assess whether it is an unproductive loop or intentional work using fresh evidence. '
            'Select your own context, retrieve omitted records if needed, and choose a recovery approach.')

    def record(self, before, after, action, entry):
        self.observe(before)
        key = self._path(before, action)
        element = next((item for item in before if item.get('ref') == action.get('ref')), {})
        state = self.map.state_id(before)
        row = self.paths.setdefault(key, self._new_path(key, state, element, action['action'], self.kind(element)))
        if not element:
            row['control'] = self._control(element, action)
            row['label'] = ('Requested ref ' + action['ref'] if action.get('ref') else
                            'Requested ' + action['action'] + ' at ' + str((action.get('x'), action.get('y'))))
        row['direction'] = action.get('direction', '')
        destination = self.map.state_id(after)
        if destination not in self.map.states:
            self.progress_version += 1
        changed = progress_identity(before) != progress_identity(after)
        verified = not any(entry.get(key) for key in ['crash', 'actionError', 'evidenceError', 'stoppingReason'])
        row['attempts'] += 1
        row['repeatedWithoutNewPath'] = (row['repeatedWithoutNewPath'] + 1
            if row.get('progressVersion') == self.progress_version else 0)
        row['progressVersion'] = self.progress_version
        row['unchangedAttempts'] = row['unchangedAttempts'] + 1 if not changed and verified else 0
        row.update(scope='in scope', planStepId=action.get('planStepId', 0))
        outcome = entry.get('crash') or entry.get('actionError') or entry.get('stoppingReason') or entry.get('evidenceError') or (
            'Observed UI changed' if changed else 'No observed UI change after the action')
        row['lastOutcome'] = outcome
        entry.update(observedOutcome=outcome, controlLabel=row['label'])
        self.transitions.append(dict(source=state, destination=destination, control=row['label'], outcome=outcome))
        self.map.record(before, after, row['control'], action['action'], outcome, verified,
            routable=verified and action['action'] != 'restart' and not entry.get('navigation') and not entry.get('recovery'))
        self.observe(after)

    def remaining(self):
        return [row['label'] + ': ' + (row['reason'] or row['scope']) for row in self.paths.values()
                if row['scope'] in ['unclassified', 'blocked'] or row['scope'] == 'in scope' and row['attempts'] == 0]

    def current_controls(self, elements):
        state = self.map.state_id(elements)
        controls = []
        for item in app_elements(elements):
            if not self.kind(item):
                continue
            action = 'swipe' if self.kind(item) == 'scroll' else 'tap'
            key = self._key(elements, item, {'action': action})
            path = self.paths.get(key, self._new_path(key, state, item, action, self.kind(item)))
            known = sum(row['attempts'] for row in self.paths.values() if row['control'] == control_identity(item))
            controls.append(dict(path, ref=item.get('ref', ''), knownAttempts=known))
        return controls

    def snapshot(self, elements, target=''):
        state = self.map.state_id(elements)
        return dict(currentScreen=state, currentControls=self.current_controls(elements), knownPaths=len(self.paths),
            pendingPlan=self.plan, pendingPaths=[dict(row) for row in self.paths.values()
                if row['scope'] != 'out of scope' and row['attempts'] == 0],
            recentTransitions=self.transitions, stalledPaths=[dict(row) for row in self.paths.values()
                if row['unchangedAttempts'] >= 3 or row['repeatedWithoutNewPath'] >= 3],
            applicationMap=dict(states=list(self.map.states.values()), configuration=self.map.configuration,
                knownStates=len(self.map.states), route=self.map.route(state, target)))

    def saved(self):
        return dict(paths=list(self.paths.values()), transitions=self.transitions, pendingPlan=self.plan,
                    applicationMap=self.map.saved())
