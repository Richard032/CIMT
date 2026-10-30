"""Translate terminal signals into the normal worker stop policy."""

import signal


class RunSignals:
    def __init__(self, control):
        self.control = control
        self.previous = {}

    def __enter__(self):
        for name in [signal.SIGINT, signal.SIGTERM]:
            self.previous[name] = signal.signal(name, self._request)
        return self

    def _request(self, number, frame):
        self.control.interrupt()

    def __exit__(self, *error):
        for name, handler in self.previous.items():
            signal.signal(name, handler)
