import unittest

from client.mouse_cursor_motion import (
    MouseCursorMotionParameters, update_mouse_cursor_motion,
)


class MouseCursorMotionTests(unittest.TestCase):
    def test_in_range_axis_deadzone_and_signed_response(self):
        p = MouseCursorMotionParameters(100, 50.0, 5.0, 200, 10)
        center = update_mouse_cursor_motion(100, p)
        self.assertEqual((center.clamped_sample, center.signed_axis,
                          center.center_frames_remaining), (100, 0, 9))
        inside = update_mouse_cursor_motion(103, p)
        self.assertEqual(inside.signed_axis, 0)
        positive = update_mouse_cursor_motion(145, p)
        negative = update_mouse_cursor_motion(55, p)
        self.assertEqual((positive.signed_axis, negative.signed_axis), (112, -112))

    def test_outside_sample_clamps_and_requests_cursor_recenter(self):
        result = update_mouse_cursor_motion(1000,
            MouseCursorMotionParameters(-10, 50.0, 5.0, 44, 7))
        self.assertEqual(result.clamped_sample, 40)
        self.assertEqual(result.signed_axis, 127)
        self.assertEqual(result.center_frames_remaining, 60)
        self.assertEqual(result.setter_calls, ((3, 1000), (4, 44)))

    def test_invalid_radius_domain_is_rejected(self):
        for radius, deadzone in ((0.0, 0.0), (5.0, 5.0), (4.0, 5.0),
                                 (5.0, -1.0)):
            with self.subTest(radius=radius, deadzone=deadzone):
                with self.assertRaises(ValueError):
                    update_mouse_cursor_motion(0,
                        MouseCursorMotionParameters(0, radius, deadzone, 0, 0))


if __name__ == '__main__':
    unittest.main()
