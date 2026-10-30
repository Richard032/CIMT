"""Shared stopping rules for all device workers."""

import threading
import time
from pathlib import Path
from errors import LimitReached


class RunControl:
    """Stops all workers when a shared limit or blocking failure occurs."""

    def __init__(self, deadline, clock=time.time, stop_file=None):
        self.deadline = deadline
        self.clock = clock
        self.stopped = threading.Event()
        self.user_interrupted = threading.Event()
        self.stop_file = Path(stop_file) if stop_file else None

    @property
    def interrupted(self):
        return self.user_interrupted.is_set() or bool(self.stop_file and self.stop_file.exists())

    def interrupt(self):
        """Signal handlers only set a flag. Normal code saves results and closes tools."""
        self.user_interrupted.set()

    def check(self):
        """Stop before the next operation if another worker stopped or time expired."""
        if self.interrupted:
            raise LimitReached("User interrupted execution; partial observations were retained")
        if self.stopped.is_set():
            raise LimitReached("Run stopped after another worker reached a blocking condition")
        if self.clock() >= self.deadline:
            self.stop()
            raise LimitReached("Whole-run time limit reached")

    def stop(self):
        """Signal every worker to stop before its next operation."""
        self.stopped.set()
