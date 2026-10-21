import struct
import unittest

from client.mouse_action_updates import MouseActionUpdateState
from client.mouse_cursor_motion import MouseCursorMotionParameters
from client.mouse_state_get import (MouseAboutState, MouseCursorGlobals,
    MouseGetStateContext, MouseScalarState)
from client.mouse_update_frame import (update_mouse_fallback_frame,
    update_mouse_input_frame)


def action_image(count):
    return bytes(count * 4)


class MouseUpdateFrameTests(unittest.TestCase):
    def test_inactive_controller_uses_fallback_actions_then_shared_ring(self):
        action_state = MouseActionUpdateState(bytearray(13), [0] * 32,
            notification_payload=b'\0' * 5)
        fallback_words = (0, 0x101, 0x201, 0x301, 0x400, 0x501, 0x601, 0x701)
        fallback_image = b''.join(word.to_bytes(4, 'little') for word in fallback_words)
        results = dict(zip(fallback_words, (0, 16, 0x12, 0x13, 0, 1, 1, 1)))
        notifications = []
        fallback, edge, transition, slot = update_mouse_fallback_frame(
            action_state, b'\0' * 48, b'\0' * 128, fallback_image,
            fallback_action_dispatch=results.__getitem__, action_active=lambda _: 0,
            priority_action_active=lambda _: 0, notify=notifications.append)
        self.assertEqual((fallback.cursor_delta, fallback.button_state_0,
                          fallback.button_state_1), (8, 0x12, 0x13))
        self.assertEqual(fallback.transition_flags, 0x72)
        self.assertEqual((edge, transition, slot), (0, 0, 1))
        self.assertEqual(action_state.button_transition_flags, 0x72)
        self.assertEqual(notifications, [b'\x08\x12\x13\x72\0'])

    def test_selector_six_motion_mapping_and_transition_ring_are_connected(self):
        cursor = MouseCursorGlobals(access_mode=0, clamp_wheel=0,
            x=100, y=200, z=0, minimum_z=-100, maximum_z=100,
            wheel_delta=0, position_mode=0, device=0x1234)
        context = MouseGetStateContext(MouseAboutState(1, bytearray(0x21c)),
            cursor, MouseScalarState(0, 0, 0))
        frame = MouseActionUpdateState(bytearray(13), [0] * 32,
            notification_payload=b'\0' * 5)
        calls = []
        sample = struct.pack('<3i4B', 100, -5, 2, 0x80, 0, 0x70, 4)

        def read_state(device, size, output):
            calls.append(('read', device, size))
            output[:] = sample
            return 0

        result = update_mouse_input_frame(
            context, frame, action_image(12), action_image(32),
            motion_parameters=MouseCursorMotionParameters(100, 20.0, 2.0, 300, 4),
            mapping_words=(12, 11, 9, 5),
            action_active=lambda _action: 0,
            priority_action_active=lambda _action: 0,
            query_absolute_cursor=lambda: None,
            ensure_device_acquired=lambda device: calls.append(('acquire', device)),
            read_device_state=read_state,
            report_error=lambda _message: calls.append(('error',)),
            set_mouse_state=lambda selector, value: calls.append(('set', selector, value)),
            notify=lambda payload: calls.append(('notify', payload)))

        self.assertEqual(calls[:2], [('acquire', 0x1234), ('read', 0x1234, 16)])
        self.assertEqual((cursor.x, cursor.y, cursor.z), (200, 195, 2))
        self.assertEqual(result.motion.clamped_sample, 120)
        self.assertEqual(result.motion.signed_axis, 127)
        self.assertEqual(result.motion.setter_calls, ((3, 200), (4, 300)))
        self.assertEqual(result.mapping.value_9e1654, 1)
        self.assertEqual(result.mapping.value_9e1658, 0)
        self.assertEqual(result.mapping.value_9e165c, 1)
        self.assertEqual((result.action_edge, result.transition_word), (1, 1 << 27))
        self.assertEqual(frame.edge_latches[1], 1)
        self.assertEqual(frame.ring_counter, 1)
        self.assertEqual(calls[-3:], [
            ('set', 3, 200), ('set', 4, 300), ('notify', b'\0\0\0\0\1')])

    def test_failed_device_read_is_zeroed_before_motion_and_mapping(self):
        cursor = MouseCursorGlobals(access_mode=0, clamp_wheel=0,
            x=50, y=60, z=0, minimum_z=-20, maximum_z=20,
            wheel_delta=0, position_mode=0, device=7)
        context = MouseGetStateContext(MouseAboutState(1, bytearray(0x21c)),
            cursor, MouseScalarState(0, 0, 0))
        frame = MouseActionUpdateState(bytearray(13), [0] * 32,
            notification_suppressed=1, notification_payload=b'\0' * 5)
        result = update_mouse_input_frame(
            context, frame, action_image(12), action_image(32),
            motion_parameters=MouseCursorMotionParameters(50, 10.0, 1.0, 0, 0),
            mapping_words=(1, 2, 3, 4), action_active=lambda _action: 0,
            priority_action_active=lambda _action: 0,
            query_absolute_cursor=lambda: None,
            ensure_device_acquired=lambda _device: None,
            read_device_state=lambda _device, _size, output: (output.__setitem__(slice(None), b'\xff' * 16) or 1),
            report_error=lambda _message: None,
            set_mouse_state=lambda _selector, _value: None)
        self.assertEqual((cursor.x, cursor.y, cursor.z), (50, 60, 0))
        self.assertEqual((result.motion.signed_axis, result.action_edge,
                          result.transition_word), (0, 0, 0))
        self.assertEqual(result.mapping.value_9e1654, 0)
        self.assertEqual(frame.ring_counter, 1)


if __name__ == '__main__':
    unittest.main()
