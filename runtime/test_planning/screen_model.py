"""Interpret adapter-neutral, already masked screen elements."""

import hashlib
import json


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def app_elements(elements):
    # Ignore only known status indicators, not permission dialogs or the keyboard.
    ignored = {'com.android.systemui:id/clock', 'com.android.systemui:id/mobile_combo'}
    return [item for item in elements if item.get('type') != 'CimtScreenInfo'
            and item.get('identifier') not in ignored]


def control_identity(element):
    name = element.get('identifier') or element.get('name')
    return identity([element.get('type', ''), name] if name else [
        element.get('type', ''), label(element), element.get('coordinates', {})])


def label(element):
    return str(element.get('label') or element.get('text') or element.get('identifier')
               or element.get('name') or element.get('type') or 'Unnamed control')


def control_kind(element):
    """Use available semantics. Unknown generic views need an AI identification."""
    kind = (element.get('type', '') + ' ' + element.get('role', '')).lower()
    if element.get('enabled') is False or element.get('visible') is False:
        return ''
    if element.get('editable') is True or any(x in kind for x in ['edittext', 'textfield', 'xcuielementtypetextview', 'entry', 'input']):
        return 'text'
    if any(x in kind for x in ['switch', 'checkbox', 'toggle']):
        return 'toggle'
    if any(x in kind for x in ['picker', 'combobox', 'spinner', 'slider']):
        return 'select'
    if element.get('scrollable') is True or any(x in kind for x in ['scrollview', 'collectionview', 'listview']):
        return 'scroll'
    if element.get('clickable') is True or any(x in kind for x in ['button', 'tab', 'radio', 'cell', 'link']):
        return 'tap'
    return ''


def view_identity(elements):
    # Values are state, not screen identity. Stable app IDs survive translated labels.
    return identity(sorted(control_identity(item) for item in app_elements(elements)))


def screen_label(elements):
    headings = [label(item) for item in app_elements(elements)
                if item.get('type', '').lower().endswith(('navigationbar', 'heading', 'header'))]
    visible = [str(item.get('label') or item.get('text') or '') for item in app_elements(elements)
               if control_kind(item) != 'text']
    return ' / '.join((headings or [text for text in visible if text])[:3])[:160] or 'Observed screen'


def progress_identity(elements):
    fields = ['identifier', 'type', 'label', 'text', 'name', 'value', 'checked', 'selected', 'enabled']
    return identity(sorted(json.dumps([item.get(key, '') for key in fields], sort_keys=True)
                           for item in app_elements(elements)))


def input_state(elements):
    """Build a structural key. Full UI text remains in the observation evidence."""
    rows = []
    for item in app_elements(elements):
        if not control_kind(item):
            continue
        values = {key: item[key] for key in ['value', 'checked', 'selected', 'enabled'] if key in item}
        if control_kind(item) == 'text' and 'text' in item:
            values['text'] = item['text']
        rows.append([control_identity(item), values])
    return sorted(rows, key=lambda row: row[0])
