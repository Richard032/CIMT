"""Mechanical execution of a single model-selected device action."""

import time
import math
from errors import InfrastructureError, LimitReached


class ActionExecutor:
    """Maps allowed actions to device calls. It cannot run shell commands."""

    def __init__(self, config, redactor, deadline, sleep=time.sleep, clock=time.time, check=lambda: None):
        self.config = config
        self.redactor = redactor
        self.deadline = deadline
        self.sleep = sleep
        self.check = check
        self.clock = clock

    def execute(self, mobile, action, elements, record_call=None):
        """Check technical constraints and execute the AI's selected action."""
        self.check()
        mobile.readiness()
        self.check()
        handlers = {
            "tap": self._tap,
            "credential": self._credential,
            "text": self._text,
            "swipe": self._swipe,
            "back": self._back,
            "wait": self._wait,
            "restart": self._restart,
        }
        handler = handlers.get(action["action"])
        if handler is None:
            raise ValueError("Unsupported action")
        if action['action'] == 'swipe':
            return handler(mobile, action, elements, record_call)
        return handler(mobile, action, elements)

    def _tap(self, mobile, action, elements):
        if action["ref"]:
            # The AI may use earlier knowledge. Let the adapter resolve its target.
            mobile.call("mobile_click_on_screen_at_coordinates", ref=action["ref"])
            return
        size = next(element for element in elements if element.get("type") == "CimtScreenInfo")
        x, y = action["x"], action["y"]
        if (
            type(x) is not int
            or type(y) is not int
            or not 0 <= x < size["screenWidth"]
            or not 0 <= y < size["screenHeight"]
        ):
            raise ValueError("Coordinate tap is outside the current device screen")
        mobile.call("mobile_click_on_screen_at_coordinates", x=x, y=y)

    def _credential(self, mobile, action, elements):
        value = self._credential_value(action)
        element = self._credential_element(action["ref"], elements)
        identifier = element.get("identifier")
        if not identifier:
            raise InfrastructureError(
                "Credential entry requires a stable element ID for reliable masking"
            )
        # Register the mask before typing. The next screenshot must hide this field.
        self.redactor.ids.add(identifier)
        mobile.call("mobile_click_on_screen_at_coordinates", ref=action["ref"])
        self.check()
        mobile.replace_text(value)
        return ('Credential field contents replaced using the configured value; adapter confirmed completion. '
                'The value is hidden. This does not confirm authentication; inspect the app after submitting.')

    def _credential_value(self, action):
        aliases = self.config.get("credentials", {})
        if action["credential"] not in aliases or action["field"] not in ["username", "password"]:
            raise ValueError("Requested credential alias/field is not configured")
        return aliases[action["credential"]][action["field"]]

    @staticmethod
    def _credential_element(ref, elements):
        current = {element.get("ref"): element for element in elements}
        if ref not in current or current[ref].get("enabled") is False:
            raise ValueError("Credential target is absent or disabled; no secret was entered")
        return current[ref]

    @staticmethod
    def _text(mobile, action, elements):
        if len(action["text"]) > 1000:
            raise ValueError("Synthetic text action is too long")
        mobile.call("mobile_type_keys", text=action["text"], submit=False)

    @staticmethod
    def _number(value):
        try:
            return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            return False

    @classmethod
    def _swipe_arguments(cls, action, elements):
        if action.get('argumentError'):
            raise ValueError(action['argumentError'])
        if action['direction'] not in ['up', 'down', 'left', 'right']:
            raise ValueError('Invalid swipe direction')
        ref, x, y = action.get('ref', ''), action.get('x', -1), action.get('y', -1)
        distance = action.get('distance')
        if not isinstance(ref, str):
            raise ValueError('Swipe ref must be a string')
        if distance is not None and (not cls._number(distance) or distance < 1):
            raise ValueError('Swipe distance must be a finite number at least 1')
        untargeted = x == -1 and y == -1
        if ref and not untargeted:
            raise ValueError('Swipe target is conflicting: provide either ref or x/y, not both')
        arguments = dict(direction=action['direction'])
        if not ref and untargeted:
            if distance is not None:
                # Mobile MCP ignores distance on its untargeted swipe path.
                raise ValueError('Swipe distance requires a target ref or x/y coordinates')
            return arguments
        if ref:
            matches = [element for element in elements if element.get('ref') == ref]
            if len(matches) != 1:
                raise ValueError('Swipe target cannot be resolved; request fresh evidence or provide coordinates')
            bounds = matches[0].get('coordinates')
            if not isinstance(bounds, dict) or not all(cls._number(bounds.get(key))
                    for key in ['x', 'y', 'width', 'height']) or bounds['width'] <= 0 or bounds['height'] <= 0:
                raise ValueError('Swipe target has no valid bounds; request fresh evidence or provide coordinates')
            x, y = bounds['x'] + bounds['width'] / 2, bounds['y'] + bounds['height'] / 2
        if not cls._number(x) or not cls._number(y) or x < 0 or y < 0:
            raise ValueError('Swipe requires both finite nonnegative x/y coordinates')
        screen = next((element for element in elements if element.get('type') == 'CimtScreenInfo'), {})
        width, height = screen.get('screenWidth'), screen.get('screenHeight')
        if not cls._number(width) or not cls._number(height) or width <= 0 or height <= 0:
            raise ValueError('Swipe screen coordinate size is unavailable')
        if not x < width or not y < height:
            raise ValueError('Swipe start is outside the current device screen')
        arguments.update(x=x, y=y)
        if distance is not None:
            arguments['distance'] = distance
        return arguments

    @classmethod
    def _swipe(cls, mobile, action, elements, record_call=None):
        arguments = cls._swipe_arguments(action, elements)
        call = dict(tool='mobile_swipe_on_screen', status='attempted',
                    arguments=dict(device=mobile.device['id'], **arguments))
        if record_call:
            record_call(call)
        try:
            mobile.call('mobile_swipe_on_screen', **arguments)
        except LimitReached:
            call['status'] = 'stopped'
            raise
        except Exception:
            call['status'] = 'failed'
            raise
        else:
            call['status'] = 'completed'

    @staticmethod
    def _back(mobile, action, elements):
        if mobile.device["platform"] != "android":
            raise ValueError("iOS has no system BACK button; choose a tap or swipe action")
        mobile.call("mobile_press_button", button="BACK")

    def _wait(self, mobile, action, elements):
        self.sleep(min(2, max(0, self.deadline - self.clock())))

    def _restart(self, mobile, action, elements):
        app_id = getattr(mobile, 'app_id', '')
        if not app_id:
            raise InfrastructureError('Restart requires the verified application identity')
        # Use the installed target, never an app ID supplied by the model. Keep app data.
        mobile.call('mobile_terminate_app', packageName=app_id)
        self.check()
        mobile.call('mobile_launch_app', packageName=app_id)
