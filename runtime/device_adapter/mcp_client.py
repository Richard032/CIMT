"""Mobile MCP pipe transport. Device policies belong to other services."""

import json
import os
import selectors
import subprocess
import threading
import time
from errors import InfrastructureError, LimitReached
from .rpc_messages import RpcMessages


class Mcp:
    """Owns one MCP connection and its redacted diagnostic log."""

    def __init__(
        self,
        folder,
        env,
        redactor,
        deadline,
        process_factory=subprocess.Popen,
        selector_factory=selectors.DefaultSelector,
        clock=time.time,
    ):
        self.deadline = deadline
        self.clock = clock
        self.redactor = redactor
        self.log = (folder / "adapter.log").open("w")
        self.p = self._start_process(env, process_factory)
        self.reader = threading.Thread(target=self._drain_diagnostics, daemon=True)
        self.reader.start()
        self.sel = selector_factory()
        self.sel.register(self.p.stdout, selectors.EVENT_READ)
        self.messages = RpcMessages()
        self.id = 0
        self._initialize()

    @staticmethod
    def _start_process(env, factory):
        env = dict(env)
        env.pop("OPENAI_API_KEY", None)
        return factory(
            ["mcp-server-mobile", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def _drain_diagnostics(self):
        for line in iter(self.p.stderr.readline, b""):
            self.log.write(self.redactor.text(line.decode(errors="replace")))
            self.log.flush()

    def _initialize(self):
        self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "cimt", "version": "0.1"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, message):
        self.p.stdin.write((json.dumps(message) + "\n").encode())
        self.p.stdin.flush()

    def request(self, method, params, timeout=45):
        if self.clock() >= self.deadline:
            raise LimitReached("Whole-run time limit reached")
        self.id += 1
        self._send({"jsonrpc": "2.0", "id": self.id, "method": method, "params": params})
        return self._wait_response(self.id, min(self.deadline, self.clock() + timeout))

    def _wait_response(self, request_id, until):
        while self.clock() < until:
            for _, _ in self.sel.select(min(1, max(0.01, until - self.clock()))):
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk:
                    raise InfrastructureError("Mobile MCP exited")
                for response in self.messages.feed(chunk):
                    matched, result = self.messages.result(response, request_id)
                    if matched:
                        return result
        if self.clock() >= self.deadline:
            raise LimitReached("Whole-run time limit reached")
        raise InfrastructureError("Mobile MCP operation timed out")

    def call(self, name, arguments, timeout=45):
        """Call one adapter tool and redact any error text before raising it."""
        value = self.request("tools/call", {"name": name, "arguments": arguments}, timeout)
        return self.messages.tool_result(value, name, self.redactor.text)

    def close(self):
        """Stop the client process and release its streams and diagnostic reader."""
        self.p.terminate()
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
        self.reader.join(2)
        self.sel.close()
        self.log.close()
