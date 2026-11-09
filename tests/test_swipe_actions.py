"""Gesture forwarding uses fake devices and the existing scenario test fixtures."""

import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from actions import ActionExecutor
from command_reply import read_reply
from errors import DeviceActionError, LimitReached
from redaction import Redactor
from test_runtime_components import FakeMobile, action, SWIPE_SCREEN as SCREEN, SWIPE_WHEEL as WHEEL
from test_command_reply import reply

class SwipeActionsTests(unittest.TestCase):
    def setUp(self):
        self.mobile = FakeMobile(Path('/unused'))
        self.executor = ActionExecutor({}, Redactor({}), float('inf'))
        self.elements = [WHEEL, SCREEN]

    def execute(self, **arguments):
        value = dict(action='swipe', direction='up', **arguments)
        command = read_reply(reply(json.dumps(value)))
        self.executor.execute(self.mobile, command, self.elements)
        return self.mobile.calls

    def test_reference_swipe_uses_wheel_centre_in_device_coordinates(self):
        self.assertEqual(self.execute(ref='@wheel', distance=40), [
            ('mobile_swipe_on_screen', dict(direction='up', x=201, y=765.5, distance=40))])

    def test_explicit_fractional_coordinates_and_distance_are_unchanged(self):
        self.assertEqual(self.execute(x=12.5, y=30.25, distance=18.75), [
            ('mobile_swipe_on_screen', dict(direction='up', x=12.5, y=30.25, distance=18.75))])

    def test_target_without_distance_preserves_the_adapter_default(self):
        self.assertEqual(self.execute(ref='@wheel'), [
            ('mobile_swipe_on_screen', dict(direction='up', x=201, y=765.5))])

    def test_untargeted_swipe_preserves_whole_screen_behavior(self):
        self.assertEqual(self.execute(), [('mobile_swipe_on_screen', dict(direction='up'))])

    def test_disabled_target_is_not_replaced_or_semantically_rejected(self):
        self.elements = [dict(WHEEL, enabled=False), SCREEN]
        self.assertTrue(self.execute(ref='@wheel', distance=35))

    def test_missing_target_does_not_fall_back_to_screen_centre(self):
        with self.assertRaisesRegex(ValueError, 'cannot be resolved'):
            self.execute(ref='@missing')
        self.assertEqual(self.mobile.calls, [])

    def test_conflicting_target_forms_are_not_silently_prioritized(self):
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            self.execute(ref='@wheel', x=201, y=765)
        self.assertEqual(self.mobile.calls, [])

    def test_distance_without_start_point_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, 'distance requires a target'):
            self.execute(distance=40)
        self.assertEqual(self.mobile.calls, [])

    def test_partial_or_invalid_coordinates_cause_no_adapter_call(self):
        for values in [dict(x=10), dict(y=10), dict(x=None,y=10), dict(x=True,y=10),
                       dict(x='10',y=10), dict(x={},y=10), dict(x=-2,y=10),
                       dict(x=math.inf,y=10), dict(x=math.nan,y=10)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.execute(**values)
        self.assertEqual(self.mobile.calls, [])

    def test_invalid_distance_cannot_turn_into_an_adapter_default(self):
        for distance in [0,-1,0.5,True,'40',[],{},math.inf,math.nan]:
            with self.subTest(distance=distance), self.assertRaisesRegex(ValueError, 'distance'):
                self.execute(ref='@wheel',distance=distance)
        self.assertEqual(self.mobile.calls, [])

    def test_invalid_reference_type_cannot_turn_into_an_untargeted_swipe(self):
        for ref in [None,123,False,{},[]]:
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'ref must be a string'):
                self.execute(ref=ref)
        self.assertEqual(self.mobile.calls, [])

    def test_missing_ambiguous_or_invalid_bounds_cause_no_adapter_call(self):
        for elements in [[dict(WHEEL, coordinates=None),SCREEN],
                         [dict(WHEEL,coordinates=dict(x=0,y=0,width=0,height=10)),SCREEN],
                         [dict(WHEEL,coordinates=dict(x=0,y=0,width=True,height=10)),SCREEN],
                         [WHEEL,dict(WHEEL),SCREEN]]:
            self.elements=elements
            with self.subTest(elements=elements), self.assertRaises(ValueError):
                self.execute(ref='@wheel')
        self.assertEqual(self.mobile.calls, [])

    def test_outside_screen_and_unavailable_screen_geometry_are_rejected(self):
        for x,y in [(402,0),(0,874),(500,900)]:
            with self.subTest(x=x,y=y), self.assertRaisesRegex(ValueError, 'outside'):
                self.execute(x=x,y=y)
        self.elements=[WHEEL]
        with self.assertRaisesRegex(ValueError, 'size is unavailable'):
            self.execute(ref='@wheel')
        self.assertEqual(self.mobile.calls, [])

    def test_actual_call_is_recorded_even_when_adapter_rejects_the_gesture(self):
        def failed(name,**arguments):
            self.mobile.calls.append((name,arguments))
            raise DeviceActionError('Synthetic swipe rejected')
        self.mobile.call=failed
        records=[]
        with self.assertRaises(DeviceActionError):
            self.executor.execute(self.mobile,action('swipe',ref='@wheel',direction='up',distance=45),
                                  self.elements,record_call=records.append)
        self.assertEqual(records,[dict(tool='mobile_swipe_on_screen',status='failed',
            arguments=dict(device='fixture',direction='up',x=201,y=765.5,distance=45))])


    def test_interrupted_adapter_call_is_recorded_as_stopped(self):
        def interrupted(name, **arguments):
            raise LimitReached('User interrupted execution')
        self.mobile.call = interrupted
        records = []
        with self.assertRaises(LimitReached):
            self.executor.execute(self.mobile, action('swipe', ref='@wheel', direction='up', distance=40),
                                  self.elements, record_call=records.append)
        self.assertEqual(records[0]['status'], 'stopped')
