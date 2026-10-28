"""Validation and execution of a single model-selected device action."""

import time
from errors import InfrastructureError


class ActionExecutor:
    """Maps allowed actions to device calls. It cannot run shell commands."""

    def __init__(self, config, redactor, deadline, sleep=time.sleep, clock=time.time):
        self.config = config
        self.redactor = redactor
        self.deadline = deadline
        self.sleep = sleep
        self.clock = clock

    def execute(self, mobile, action, elements):
        """Validate and execute one allowed action on the current screen."""
        mobile.readiness()
        handlers = {
            "tap": self._tap,
            "credential": self._credential,
            "text": self._text,
            "swipe": self._swipe,
            "back": self._back,
            "wait": self._wait,
        }
        handler = handlers.get(action["action"])
        if handler is None:
            raise ValueError("Unsupported action")
        handler(mobile, action, elements)

    def _tap(self, mobile, action, elements):
        if action["ref"]:
            self._element(action["ref"], elements)
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
        element = self._element(action["ref"], elements)
        identifier = element.get("identifier")
        if not identifier:
            raise InfrastructureError(
                "Credential entry requires a stable element ID for reliable masking"
            )
        # Register the mask before typing. The next screenshot must hide this field.
        self.redactor.ids.add(identifier)
        mobile.call("mobile_click_on_screen_at_coordinates", ref=action["ref"])
        mobile.call("mobile_type_keys", text=value, submit=False)

    def _credential_value(self, action):
        aliases = self.config.get("credentials", {})
        if action["credential"] not in aliases or action["field"] not in ["username", "password"]:
            raise ValueError("Requested credential alias/field is not configured")
        return aliases[action["credential"]][action["field"]]

    @staticmethod
    def _element(ref, elements):
        current = {element.get("ref"): element for element in elements}
        if ref not in current or current[ref].get("enabled") is False:
            raise ValueError("Action ref is absent or disabled on the current screen")
        return current[ref]

    @staticmethod
    def _text(mobile, action, elements):
        if len(action["text"]) > 1000:
            raise ValueError("Synthetic text action is too long")
        mobile.call("mobile_type_keys", text=action["text"], submit=False)

    @staticmethod
    def _swipe(mobile, action, elements):
        if action["direction"] not in ["up", "down", "left", "right"]:
            raise ValueError("Invalid swipe direction")
        mobile.call("mobile_swipe_on_screen", direction=action["direction"])

    @staticmethod
    def _back(mobile, action, elements):
        if mobile.device["platform"] != "android":
            raise ValueError("On iOS choose an observed back-button ref")
        mobile.call("mobile_press_button", button="BACK")

    def _wait(self, mobile, action, elements):
        self.sleep(min(2, max(0, self.deadline - self.clock())))
