"""Local storage of redacted results and already masked screen evidence."""

import json
import pathlib
import threading
import hashlib
from errors import InfrastructureError


def atomic(path, value):
    """Replace a result file only after the new JSON is fully written."""
    path = pathlib.Path(path)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


class RunJournal:
    """Serializes worker snapshots without reading a dictionary being changed."""

    def __init__(self, root, redactor, budget, run_id=""):
        self.run_id = run_id
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
        safe = self.redactor.records.device_result(result)
        with self.lock:
            self.results = [item for item in self.results if item["index"] != result["index"]] + [
                safe
            ]
            self.save()

    def save(self):
        with self.lock:
            atomic(
                self.root / "ui-results.json",
                {"runId": self.run_id, "devices": self.results, "budget": self.budget.snapshot()},
            )


class ScenarioEvidence:
    """Saves masked evidence for one scenario, using report-relative links."""

    def __init__(self, folder, report):
        self.folder = pathlib.Path(folder)
        self.report = pathlib.Path(report)
        self.images = {}

    def save_image(self, name, image):
        path = self.folder / name
        relative = str(path.relative_to(self.report))
        digest = hashlib.sha256(image).hexdigest()
        if relative in self.images and self.images[relative]['sha256'] != digest:
            # A repeated evidence name must not replace an earlier observed image.
            path = path.with_name(path.stem + '-capture-' + str(len(self.images)) + path.suffix)
            relative = str(path.relative_to(self.report))
        identifier = self.images.get(relative, {}).get('id', len(self.images))
        path.write_bytes(image)
        self.images[relative] = dict(id=identifier, path=relative, sha256=digest)
        return relative

    def load_images(self, selected):
        """Read only AI-selected images that still match the masked evidence we saved."""
        images = []
        for row in selected:
            expected = self.images.get(row['path'])
            path = (self.report / row['path']).resolve()
            if expected != row or not path.is_relative_to(self.report.resolve()):
                raise InfrastructureError('Selected screenshot is not registered masked evidence')
            try:
                content = path.read_bytes()
            except OSError:
                raise InfrastructureError('Selected masked screenshot is unavailable') from None
            if hashlib.sha256(content).hexdigest() != row['sha256']:
                raise InfrastructureError('Selected masked screenshot changed after capture')
            images.append(dict(id=row['id'], image=content))
        return images

    def save_step(self, index, elements, image):
        name = "step-" + str(index).zfill(4)
        screenshot = self.save_image(name + ".png", image)
        ui = self.folder / (name + "-ui.json")
        atomic(ui, elements)
        return {"screenshot": screenshot, "ui": str(ui.relative_to(self.report))}
