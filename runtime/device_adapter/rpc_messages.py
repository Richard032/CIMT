"""Line-based JSON-RPC messages without process or device access."""

import json
from errors import AppLaunchError, DeviceActionError, InfrastructureError

INTERACTION_TOOLS = {
    'mobile_click_on_screen_at_coordinates', 'mobile_type_keys',
    'mobile_swipe_on_screen', 'mobile_press_button',
}


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
        """Translate an answered tool result without hiding connection failures."""
        if not value.get("isError"):
            return value
        message = redact(" ".join(
            item.get("text", "") for item in value.get("content", [])
        ))
        # Connection errors are raised before this boundary. Interactions return feedback.
        if name == 'mobile_launch_app':
            raise AppLaunchError(message)
        if name in INTERACTION_TOOLS:
            raise DeviceActionError(message)
        raise InfrastructureError(message)
