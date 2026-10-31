"""Tracks observed controls. Counts do not prove exhaustive app coverage."""

import hashlib
import json


def element_key(element):
    return json.dumps(
        [element.get(key, "") for key in ["identifier", "type", "label", "text", "name"]],
        sort_keys=True,
    )


def screen_key(elements):
    value = json.dumps([element_key(element) for element in elements], sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class CoverageTracker:
    """Remembers which observed control/state combinations were activated."""

    def __init__(self):
        self.observed = {}
        self.attempted = set()
        self.state = ""

    def observe(self, elements):
        """Add enabled controls from the current screen to the coverage record."""
        self.state = screen_key(elements)
        for element in elements:
            if self.is_control(element):
                label = (
                    element.get("label")
                    or element.get("text")
                    or element.get("identifier")
                    or element.get("type")
                )
                self.observed[self._key(element)] = label

    @staticmethod
    def is_control(element):
        kinds = ["button", "switch", "checkbox", "tab", "radio", "cell"]
        return element.get("enabled") is not False and any(
            kind in element.get("type", "").lower() for kind in kinds
        )

    def activated(self, element):
        """Count a control only after its action was accepted."""
        key = self._key(element)
        if key in self.observed:
            self.attempted.add(key)

    def outstanding(self):
        return {key: label for key, label in self.observed.items() if key not in self.attempted}

    def snapshot(self):
        """Report observed and activated controls without claiming hidden-state coverage."""
        outstanding = self.outstanding()
        return {
            "observedControls": len(self.observed),
            "attemptedControls": len(self.attempted),
            "outstandingObservedControls": len(outstanding),
            "outstandingExamples": list(outstanding.values()),
        }

    def _key(self, element):
        return self.state + ":" + element_key(element)

    def crash_point(self, target, element, action):
        fallback = (
            element_key(element)
            if element
            else action["action"] + action.get("direction", "") + str((action["x"], action["y"]))
        )
        return target + ":" + (element.get("identifier") or self.state + ":" + fallback)
