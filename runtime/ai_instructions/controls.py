"""Describe adapter-declared human controls without choosing an action."""

from test_planning.screen_model import declared_control_kind


def human_interface(elements):
    """Keep availability flags as information. They do not approve AI targets."""
    controls = []
    for element in elements:
        kind = declared_control_kind(element)
        if kind:
            controls.append(dict(element, inputKind=kind))
    return controls
