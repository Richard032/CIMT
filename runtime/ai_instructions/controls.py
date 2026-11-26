"""Describe possible UI targets without choosing an action."""

from test_planning.screen_model import declared_control_kind


def human_interface(elements):
    """Preserve adapter metadata without assuming how a target can be used."""
    return [element for element in elements
            if element.get('type') != 'TestPilotScreenInfo'
            and (element.get('identifier') or declared_control_kind(element))]
