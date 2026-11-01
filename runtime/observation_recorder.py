"""Register verified masked observations and factual operating-system warnings."""

import hashlib
from datetime import datetime, timezone
from device_adapter.warnings import android_anr
from test_planning.screen_model import identity


class ObservationRecorder:
    """Adds evidence references and warning records; it never selects app actions."""

    def __init__(self, device, target, activity=None):
        self.device = device
        self.target = target
        self.activity = activity
        self.active_anr = None

    def record(self, session, references, step, action_result=False):
        # Recovery screens must also remain retrievable by their observation IDs.
        session.planner.observe(session.elements)
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        warnings = self._warnings(session, step, timestamp)
        observation = dict(id=identity([session.elements, hashlib.sha256(session.image).hexdigest()]),
            screen=session.planner.memory.map.state_id(session.elements),
            uiObservation=identity(session.elements), timestamp=timestamp, **references)
        session.feedback.observe(observation, warnings, action_result)
        return observation['id']

    def _warnings(self, session, step, timestamp):
        if not android_anr(self.device, session.elements):
            self.active_anr = None
            return []
        if self.active_anr is None:
            rows = session.result.setdefault('warnings', [])
            self.active_anr = dict(id=len(rows), code='android-anr', level='warning',
                timestamp=timestamp, step=step, device=self.device.get('id', ''),
                platform='android', target=self.target,
                message='Android reports that the application is not responding (ANR).')
            rows.append(self.active_anr)
            if self.activity:
                self.activity.write('Android ANR', 'warning',
                    'Step ' + str(step) + ': ' + self.active_anr['message'], self.device, self.target)
        return [self.active_anr]
