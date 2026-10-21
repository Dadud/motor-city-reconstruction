import struct
import unittest

from client.mouse_state_get import (MouseAboutState, MouseCursorGlobals, MouseScalarState,
    MouseGetStateContext, get_mouse_about_state, get_mouse_invalid_state,
    get_mouse_state,
    get_mouse_cursor_state_absolute, get_mouse_cursor_state_direct_input,
    get_mouse_scalar_state)


class MouseStateGetTests(unittest.TestCase):
    def test_device_info_success_returns_mutated_shared_buffer(self):
        state = MouseAboutState(1, bytearray(0x21c))
        errors = []

        def query(buffer):
            buffer[:4] = b'INFO'
            return 0

        result = get_mouse_about_state(
            state, query_device_info=query, report_error=errors.append)
        self.assertIs(result, state.information)
        self.assertEqual(state.information[:4], b'INFO')
        self.assertEqual(errors, [])

    def test_device_info_failure_returns_null_without_error_log(self):
        state = MouseAboutState(1, bytearray(0x21c))
        errors = []
        result = get_mouse_about_state(
            state, query_device_info=lambda buffer: 0x80004005,
            report_error=errors.append)
        self.assertIsNone(result)
        self.assertEqual(errors, [])

    def test_uninitialized_device_emits_fixed_diagnostic_and_preserves_buffer(self):
        info = bytearray(b'Z' * 0x21c)
        state = MouseAboutState(0, info, 0x1234, 0x5678)
        calls = []
        result = get_mouse_about_state(
            state, query_device_info=lambda _: self.fail('must not query'),
            report_error=calls.append)
        self.assertIsNone(result)
        self.assertEqual((state.diagnostic_file, state.diagnostic_line),
                         (0x84A004, 0x24a))
        self.assertEqual(calls, [0x84A0A8])
        self.assertEqual(info, b'Z' * 0x21c)

    def test_invalid_selector_reports_exact_source_line_and_message(self):
        state = MouseAboutState(0, bytearray(0x21c))
        calls = []
        self.assertIsNone(get_mouse_invalid_state(state, report_error=calls.append))
        self.assertEqual((state.diagnostic_file, state.diagnostic_line),
                         (0x84A004, 0x256))
        self.assertEqual(calls, [0x84A088])

    def test_dispatch_routes_selector_six_and_scalar_selectors(self):
        about = MouseAboutState(1, bytearray(0x21c))
        cursor = MouseCursorGlobals(4, 0, 1, 2, 3, -10, 10, 4)
        scalar = MouseScalarState(4, 3, 1)
        context = MouseGetStateContext(about, cursor, scalar)
        result = get_mouse_state(6, context,
            query_device_info=lambda _buffer: self.fail('unexpected device info'),
            query_absolute_cursor=lambda: (3, 800, 600),
            ensure_device_acquired=lambda _device: self.fail('unexpected DirectInput'),
            read_device_state=lambda *_: self.fail('unexpected DirectInput'),
            report_error=lambda _message: self.fail('unexpected diagnostic'))
        self.assertIs(result, cursor)
        self.assertEqual((cursor.x, cursor.y, cursor.z), (800, 600, 7))
        self.assertEqual(get_mouse_state(7, context,
            query_device_info=lambda _buffer: 0,
            query_absolute_cursor=lambda: (0, 0, 0),
            ensure_device_acquired=lambda _device: None,
            read_device_state=lambda _device, _size, output: output.__setitem__(
                slice(None), bytes(len(output))) or 0,
            report_error=lambda _message: None), 4)

    def test_dispatch_composes_device_read_and_zeroes_failed_directinput_state(self):
        about = MouseAboutState(1, bytearray(0x21c))
        cursor = MouseCursorGlobals(2, 0, 10, 20, 30, -100, 100, 0,
                                    position_mode=3, device=0x1234)
        context = MouseGetStateContext(about, cursor, MouseScalarState(2, 3, 0))
        calls = []

        def read(device, size, output):
            calls.append(('read', device, size))
            output[:] = struct.pack('<3i4B', 7, 8, 9, 1, 2, 3, 4)
            return 0x80004005

        result = get_mouse_state(
            6, context, query_device_info=lambda _buffer: 0,
            query_absolute_cursor=lambda: self.fail('wrong access mode'),
            ensure_device_acquired=lambda device: calls.append(('acquire', device)),
            read_device_state=read,
            report_error=lambda _message: self.fail('unexpected diagnostic'))
        self.assertIs(result, cursor)
        self.assertEqual(calls, [('acquire', 0x1234), ('read', 0x1234, 16)])
        self.assertEqual((cursor.x, cursor.y, cursor.z), (0, 0, 0))
        self.assertEqual((cursor.button0, cursor.button1, cursor.button2,
                          cursor.auxiliary_button), (0, 0, 0, 0))

    def test_scalar_state_selectors(self):
        state = MouseScalarState(0x80004005, 0x12345678, 0xffffffff)
        self.assertEqual(get_mouse_scalar_state(7, state), 0x80004005)
        self.assertEqual(get_mouse_scalar_state(8, state), 0x12345678)
        self.assertEqual(get_mouse_scalar_state(9, state), 0xffffffff)

    def test_non_scalar_selector_is_not_silently_guessed(self):
        with self.assertRaises(NotImplementedError):
            get_mouse_scalar_state(6, MouseScalarState(4, 3, 0))

    def test_absolute_cursor_position_wheel_clamp_and_button_projection(self):
        state = MouseCursorGlobals(4, 1, 10, 20, 50, 0, 100, 80)
        result = get_mouse_cursor_state_absolute(
            state, button_state=5, cursor_x=640, cursor_y=-20)
        self.assertIs(result, state)
        self.assertEqual((state.x, state.y, state.z), (640, -20, 100))
        self.assertEqual((state.wheel_delta, state.auxiliary_button), (0, 0))
        self.assertEqual((state.button0, state.button1, state.button2),
                         (0x70, 0, 0x70))

    def test_unclamped_wheel_wraps_as_x86_int32_and_directinput_is_open(self):
        state = MouseCursorGlobals(4, 0, 0, 0, 0x7fffffff, -5, 5, 1)
        get_mouse_cursor_state_absolute(state, button_state=2,
                                       cursor_x=0, cursor_y=0)
        self.assertEqual(state.z, -0x80000000)
        self.assertEqual(state.button1, 0x70)
        state.access_mode = 3
        with self.assertRaises(NotImplementedError):
            get_mouse_cursor_state_absolute(state, button_state=0,
                                            cursor_x=0, cursor_y=0)

    def test_directinput_absolute_sample_copies_position_and_all_buttons(self):
        state = MouseCursorGlobals(1, 1, 10, 20, 30, -5, 5, 2,
                                   position_mode=3)
        sample = struct.pack('<3i4B', -100, 200, 300, 1, 0x70, 0xff, 4)
        get_mouse_cursor_state_direct_input(state, sample)
        self.assertEqual((state.x, state.y, state.z), (-100, 200, 300))
        self.assertEqual((state.button0, state.button1, state.button2,
                          state.auxiliary_button), (1, 0x70, 0xff, 4))

    def test_directinput_relative_sample_wraps_or_clamps_each_axis(self):
        sample = struct.pack('<3i4B', 8, -8, 15, 1, 2, 3, 4)
        state = MouseCursorGlobals(2, 0, 4, -4, 0, -10, 10, 0,
                                   minimum_x=-5, maximum_x=5,
                                   minimum_y=-6, maximum_y=6)
        get_mouse_cursor_state_direct_input(state, sample)
        self.assertEqual((state.x, state.y, state.z), (12, -12, 15))
        state = MouseCursorGlobals(2, 1, 4, -4, 0, -10, 10, 0,
                                   minimum_x=-5, maximum_x=5,
                                   minimum_y=-6, maximum_y=6)
        get_mouse_cursor_state_direct_input(state, sample)
        self.assertEqual((state.x, state.y, state.z), (5, -6, 10))


if __name__ == '__main__':
    unittest.main()
