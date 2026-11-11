"""Keep an ordered conversation and omit previously supplied records."""

import json
from copy import deepcopy


def without_historical_images(message):
    """Preserve prior text while omitting image payloads."""
    if message.get('role') != 'user' or not isinstance(message.get('content'), list):
        return message
    content = [
        dict(type='input_text', text='[Screenshot omitted from conversation history.]')
        if item.get('type') == 'input_image' else deepcopy(item)
        for item in message['content']
    ]
    return dict(message, content=content)


def _field(data, path):
    value = data
    for name in path[:-1]:
        if not isinstance(value, dict) or name not in value:
            return None, None
        value = value[name]
    return (value, path[-1]) if isinstance(value, dict) else (None, None)


def _identity(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class Conversation:
    """Retain ordered messages and track records already supplied in them."""

    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self._seen_records = {}
        self._pending_records = {}
        self._seen_stable = {}
        self._pending_stable = {}
        self._resend_records = False

    def prepare(self, state, stable_fields, record_paths):
        """Return a message state containing new or changed records only."""
        # JSON values are already serializable and need an independent copy.
        result = json.loads(json.dumps(state, ensure_ascii=False))
        self._pending_stable = {}
        for name in stable_fields:
            if name not in result:
                continue
            value = _identity(result[name])
            self._pending_stable[name] = value
            if self._seen_stable.get(name) == value:
                result.pop(name)
        self._pending_records = {}
        for path in record_paths:
            parent, key = _field(result, path)
            if parent is None or not isinstance(parent.get(key), list):
                continue
            self._pending_records[path] = {_identity(row) for row in parent[key]}
            seen = set() if self._resend_records else self._seen_records.get(path, set())
            parent[key] = [row for row in parent[key] if _identity(row) not in seen]
        return result

    def record(self, user_message, assistant_reply):
        """Record a completed exchange and its current record versions."""
        self._seen_records = self._pending_records
        self._pending_records = {}
        self._seen_stable.update(self._pending_stable)
        self._pending_stable = {}
        self.messages.append(without_historical_images(user_message))
        self.messages.append(dict(role='assistant', content=assistant_reply))
        self._resend_records = False

    def request_records(self):
        """Send explicitly requested records again on the next exchange."""
        self._resend_records = True

    def build_messages(self, system_message, current_message):
        """Return the prior turns in order, followed by the current message."""
        return [system_message, *(without_historical_images(row) for row in self.messages), current_message]
