"""Local storage of redacted results and already masked screen evidence."""

import json
import pathlib
import threading


def atomic(path, value):
    """Replace a result file only after the new JSON is fully written."""
    path = pathlib.Path(path)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


class RunJournal:
    """Serializes worker snapshots without reading a dictionary being changed."""

    def __init__(self, root, redactor, budget):
        self.root = pathlib.Path(root)
        self.redactor = redactor
        self.budget = budget
        self.lock = threading.RLock()
        self.results = []

    def journal_budget(self):
        with self.lock:
            atomic(self.root / "ai-budget.json", self.budget.snapshot())

    def publish(self, result):
        # Copy and redact in the owning worker before sharing the result.
        safe = self.redactor.object(result)
        with self.lock:
            self.results = [item for item in self.results if item["index"] != result["index"]] + [
                safe
            ]
            self.save()

    def save(self):
        with self.lock:
            atomic(
                self.root / "ui-results.json",
                {"devices": self.results, "budget": self.budget.snapshot()},
            )


class ScenarioEvidence:
    """Saves masked evidence for one scenario, using report-relative links."""

    def __init__(self, folder, report):
        self.folder = pathlib.Path(folder)
        self.report = pathlib.Path(report)

    def save_image(self, name, image):
        path = self.folder / name
        path.write_bytes(image)
        return str(path.relative_to(self.report))

    def save_step(self, index, elements, image):
        name = "step-" + str(index).zfill(4)
        screenshot = self.save_image(name + ".png", image)
        ui = self.folder / (name + "-ui.json")
        atomic(ui, elements)
        return {"screenshot": screenshot, "ui": str(ui.relative_to(self.report))}
