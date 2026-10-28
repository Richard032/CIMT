"""Shared stopping rules for all device workers."""

import threading
import time
from errors import LimitReached


class RunControl:
    """Stops all workers when a shared limit or blocking failure occurs."""

    def __init__(self, deadline, clock=time.time):
        self.deadline = deadline
        self.clock = clock
        self.stopped = threading.Event()

    def check(self):
        """Stop before the next operation if another worker stopped or time expired."""
        if self.stopped.is_set():
            raise LimitReached("Run stopped after another worker reached a blocking condition")
        if self.clock() >= self.deadline:
            self.stop()
            raise LimitReached("Whole-run time limit reached")

    def stop(self):
        """Signal every worker to stop before its next operation."""
        self.stopped.set()
