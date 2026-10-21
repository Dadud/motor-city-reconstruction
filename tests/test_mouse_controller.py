import unittest

from client.mouse_controller import (clamp_i32, cursor_control_ready,
                                     cursor_reset_action)


class MouseControllerTests(unittest.TestCase):
    def test_i32_clamp_boundaries_and_inverted_bounds(self):
        self.assertEqual(clamp_i32(-4, -3, 7), -3)
        self.assertEqual(clamp_i32(9, -3, 7), 7)
        self.assertEqual(clamp_i32(2, -3, 7), 2)
        self.assertEqual(clamp_i32(2, 7, -3), -3)
        for values in ((1 << 31, 0, 1), (0, -(1 << 31) - 1, 1)):
            with self.assertRaises(ValueError):
                clamp_i32(*values)

    def test_readiness_requires_both_controller_flags(self):
        self.assertFalse(cursor_control_ready(0, 1))
        self.assertFalse(cursor_control_ready(1, 0))
        self.assertTrue(cursor_control_ready(1, 1))

    def test_reset_positions_mouse_only_outside_exclusive_input_modes(self):
        for mode in (0, 1, 2, 3, 6, 7):
            calls = []
            self.assertTrue(cursor_reset_action(
                enabled=1, initialized=1, input_mode=mode, environment_mode=0,
                x=123, y=456,
                set_state=lambda selector, value: calls.append((selector, value))))
            self.assertEqual(calls, [(3, 123), (4, 456)])
        for mode in (4, 5):
            calls = []
            self.assertFalse(cursor_reset_action(
                enabled=1, initialized=1, input_mode=mode, environment_mode=0,
                x=123, y=456,
                set_state=lambda selector, value: calls.append((selector, value))))
            self.assertEqual(calls, [])

    def test_unavailable_controller_skips_and_setter_failure_short_circuits(self):
        calls = []
        self.assertFalse(cursor_reset_action(
            enabled=1, initialized=0, input_mode=0, environment_mode=0,
            x=2, y=3,
            set_state=lambda selector, value: calls.append((selector, value))))
        self.assertEqual(calls, [])
        calls = []
        self.assertFalse(cursor_reset_action(
            enabled=1, initialized=1, input_mode=0, environment_mode=0,
            x=2, y=3,
            set_state=lambda selector, value: calls.append((selector, value)) or False))
        self.assertEqual(calls, [(3, 2)])

    def test_environment_mode_blocks_cursor_updates(self):
        calls = []
        self.assertFalse(cursor_reset_action(
            enabled=1, initialized=1, input_mode=0, environment_mode=1,
            x=2, y=3,
            set_state=lambda selector, value: calls.append((selector, value))))
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
