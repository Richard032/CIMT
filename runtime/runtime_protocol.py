"""Versioned private JSON exchanged with the TestPilot host."""

import json
import math
from errors import InfrastructureError


VERSION = 1


def _object(value, label):
    if not isinstance(value, dict):
        raise InfrastructureError(f'{label} must be a JSON object')
    version = value.get('protocolVersion', VERSION)
    if type(version) is not int or version != VERSION:
        raise InfrastructureError(f'Unsupported {label} protocol version; install matching TestPilot host and runtime')
    return value


def read_request(stream, *, proposal=False):
    try:
        value = _object(json.load(stream), 'worker request')
    except (ValueError, UnicodeError):
        raise InfrastructureError('Worker request must be valid JSON') from None
    fields = dict(config=dict, report=str, inputs=dict)
    fields.update(dict(outcome=dict) if proposal else dict(devices=list, builds=list))
    for name, kind in fields.items():
        if not isinstance(value.get(name), kind):
            raise InfrastructureError(f'Worker request requires {name} ({kind.__name__})')
    deadline = value.get('deadline')
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise InfrastructureError('Worker request requires a finite deadline')
    return value


def read_results(path):
    """Load saved devices, including unversioned results from early installations."""
    if not path.exists():
        return []
    try:
        value = _object(json.loads(path.read_text(encoding='utf-8')), 'worker results')
    except (ValueError, UnicodeError):
        raise InfrastructureError('Worker results must be valid JSON') from None
    devices = value.get('devices')
    if not isinstance(devices, list):
        raise InfrastructureError('Worker results require a devices array')
    return devices
