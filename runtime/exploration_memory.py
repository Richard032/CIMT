"""Remember explored paths and observed outcomes for the whole scenario."""

import hashlib
import json
from coverage_tracker import CoverageTracker, element_key
from errors import NoProgressAction


def control_identity(element):
    """Device refs can change at every capture. Prefer application identifiers."""
    identity = element.get("identifier") or element.get("name")
    if identity:
        return json.dumps([element.get("type", ""), identity], sort_keys=True)
    label = element.get("label") or element.get("text") or ""
    return json.dumps([element.get("type", ""), label, element.get("coordinates", {})], sort_keys=True)


def view_identity(elements):
    """Ignore changing values and element order when identifying a navigation view."""
    controls = sorted(control_identity(item) for item in elements if CoverageTracker.is_control(item))
    headings = sorted(str(item.get("label", "")) for item in elements
                      if item.get("type", "").lower() in ["navigationbar", "heading", "header"])
    return hashlib.sha256(json.dumps([controls, headings]).encode()).hexdigest()[:16]


class ExplorationMemory:
    """Store all attempts locally and send a bounded view of relevant progress to AI."""

    def __init__(self):
        self.paths = {}
        self.transitions = []
        self.plan = []
        self.views = set()
        self.progress_version = 0

    def _path(self, elements, action):
        element = next((item for item in elements if item.get("ref") == action.get("ref")), {})
        return self._key(view_identity(elements), element, action)

    @staticmethod
    def _key(screen, element, action):
        target = control_identity(element) if element else json.dumps([
            action["action"], action.get("x"), action.get("y"), action.get("direction", ""),
        ])
        return screen + ":" + target + ":" + json.dumps([
            action["action"], action.get("direction", ""),
        ])

    def observe(self, elements):
        """Keep untried controls after leaving a view; old refs are never stored."""
        current = view_identity(elements)
        added = current not in self.views
        self.views.add(current)
        for element in elements:
            if not CoverageTracker.is_control(element):
                continue
            key = self._key(current, element, {"action": "tap"})
            if key not in self.paths:
                self.paths[key] = self._new_path(current, element, "tap")
                added = True
        if added:
            self.progress_version += 1

    @staticmethod
    def _new_path(screen, element, action):
        return {
            "screen": screen, "control": control_identity(element),
            "label": element.get("label") or element.get("identifier") or action,
            "attempts": 0, "unchangedAttempts": 0, "repeatedWithoutNewPath": 0,
        }

    def validate(self, elements, action, instructions):
        if action["action"] not in ["tap", "swipe", "back", "text", "credential"]:
            return
        path = self.paths.get(self._path(elements, action), {})
        repeated_cycle = (path.get("repeatedWithoutNewPath", 0) >= 3
                          and path.get("progressVersion") == self.progress_version)
        if path.get("unchangedAttempts", 0) < 3 and not repeated_cycle:
            return
        quote = action.get("repeatInstruction", "")
        if quote.strip() and quote in instructions and action.get("repeatReason", "").strip():
            return
        raise NoProgressAction(
            "This action already repeated without an observed UI change or a new explored path. "
            "Choose another control or return path, or finish blocked with remaining work. "
            "Repeat only when repeatInstruction quotes an explicit repeat test and repeatReason explains it."
        )

    def record(self, before, after, action, entry):
        self.observe(before)
        key = self._path(before, action)
        destination = view_identity(after)
        if key not in self.paths or destination not in self.views:
            self.progress_version += 1
        self.views.update([view_identity(before), destination])
        element = next((item for item in before if item.get("ref") == action.get("ref")), {})
        row = self.paths.setdefault(key, self._new_path(view_identity(before), element, action["action"]))
        changed = sorted(element_key(item) for item in before) != sorted(element_key(item) for item in after)
        row["attempts"] += 1
        row["repeatedWithoutNewPath"] = (
            row.get("repeatedWithoutNewPath", 0) + 1
            if row.get("progressVersion") == self.progress_version else 0
        )
        row["progressVersion"] = self.progress_version
        row["unchangedAttempts"] = (
            row["unchangedAttempts"] + 1 if not changed and not entry.get("crash") and not entry.get("evidenceError") else 0
        )
        outcome = entry.get("crash") or entry.get("actionError") or entry.get("evidenceError") or (
            "Observed UI changed" if changed else "No observed UI change after the action"
        )
        row["lastOutcome"] = outcome
        entry["observedOutcome"] = outcome
        entry["controlLabel"] = row["label"]
        self.transitions.append({
            "from": view_identity(before), "to": view_identity(after),
            "control": row["label"], "outcome": outcome,
        })
        self.observe(after)

    def snapshot(self, elements):
        current = view_identity(elements)
        controls = []
        for item in elements:
            if not CoverageTracker.is_control(item):
                continue
            path = self.paths.get(self._key(current, item, {"action": "tap"}), {})
            controls.append({
                "ref": item.get("ref", ""),
                "label": item.get("label") or item.get("identifier") or item.get("type"),
                "attempts": path.get("attempts", 0),
                "unchangedAttempts": path.get("unchangedAttempts", 0),
                "repeatedWithoutNewPath": path.get("repeatedWithoutNewPath", 0),
                "lastOutcome": path.get("lastOutcome", "Not attempted"),
            })
        return {
            "currentScreen": current, "currentControls": controls[:80],
            "knownPaths": len(self.paths), "pendingPlan": self.plan,
            "pendingPaths": [row for row in self.paths.values() if row["attempts"] == 0][:40],
            "recentTransitions": self.transitions[-12:],
            "stalledPaths": [row for row in self.paths.values()
                             if row["unchangedAttempts"] >= 3 or row["repeatedWithoutNewPath"] >= 3][:40],
        }

    def saved(self):
        return {"paths": list(self.paths.values()), "transitions": self.transitions, "pendingPlan": self.plan}
