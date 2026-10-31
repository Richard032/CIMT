"""Timestamped diagnostics for device operations. Never record prompts or raw UI text."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
import traceback
from errors import LimitReached


class ActivityLog:
    """Append complete records under one lock shared by the device workers."""

    def __init__(self, report, redactor, output=None, clock=time.monotonic, interrupted=lambda: False):
        self.path = Path(report) / "activity.jsonl"
        self.redactor = redactor
        self.output = output if output is not None else sys.stderr
        self.clock = clock
        self.interrupted = interrupted
        self.lock = threading.Lock()

    def write(self, operation, status, message="", device=None, target="", seconds=None, error=None, log=""):
        device = device or {}
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "operation": operation,
            "status": status,
            "message": self.redactor.text(message),
            "platform": device.get("platform", ""),
            "device": device.get("id", ""),
            "target": target,
            "durationSeconds": seconds,
            "exceptionType": type(error).__name__ if error else "",
            "details": self._stack(error) if error else "",
            "log": log,
        }
        with self.lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            context = "/".join(filter(None, [entry["platform"], entry["device"], target]))
            print("CIMT activity: " + entry["timestamp"] + " [" + context + "] "
                  + operation + " — " + status
                  + (" (" + format(seconds, ".3f") + " seconds)" if seconds is not None else "")
                  + ": " + entry["message"], file=self.output, flush=True)

    @contextmanager
    def operation(self, name, device=None, target=""):
        self.write(name, "started", device=device, target=target)
        started = self.clock()
        try:
            yield
        except Exception as error:
            # Closing an interrupted adapter can raise a pipe error. Report the known stop.
            reported = (LimitReached("User interrupted execution; partial observations were retained")
                        if self.interrupted() else error)
            self.write(name, self.stop_status(reported), str(reported), device, target,
                       max(0, self.clock() - started), error=reported)
            if reported is error:
                raise
            raise reported from None
        else:
            self.write(name, "completed", device=device, target=target,
                       seconds=max(0, self.clock() - started))

    @staticmethod
    def stop_status(error):
        if isinstance(error, LimitReached):
            return "cancelled" if str(error).startswith("Run stopped after another worker") else "stopped"
        return "failed"

    def _stack(self, error):
        # Record locations only. Source lines and local variables can contain credentials.
        frames = traceback.extract_tb(error.__traceback__)
        return self.redactor.text("\n".join(
            frame.filename + ":" + str(frame.lineno) + " in " + frame.name for frame in frames
        ))
