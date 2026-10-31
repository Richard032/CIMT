"""Line-based JSON-RPC messages without process or device access."""

import json
from errors import AppLaunchError, InfrastructureError


class RpcMessages:
    """Keeps partial bytes until a complete JSON line arrives."""

    def __init__(self):
        self.buffer = b""

    def feed(self, chunk):
        self.buffer += chunk
        messages = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                messages.append(json.loads(line))
            except ValueError:
                continue
        return messages

    @staticmethod
    def result(response, request_id):
        """Ignore notifications and responses belonging to another request."""
        if response.get("id") != request_id:
            return False, None
        if "error" in response:
            raise InfrastructureError("Mobile MCP protocol error")
        return True, response["result"]

    @staticmethod
    def tool_result(value, name, redact):
        """Distinguish a rejected app launch from a failed MCP connection."""
        if value.get("isError"):
            message = redact(" ".join(
                item.get("text", "") for item in value.get("content", [])
            ))
            # Only an answered launch request is local. Transport errors stay global.
            error_type = AppLaunchError if name == "mobile_launch_app" else InfrastructureError
            raise error_type(message)
        return value
