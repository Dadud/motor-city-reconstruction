import math
import unittest

from client.tire_response import WheelCurveInput, wheel_response, f32


class TireResponseTests(unittest.TestCase):
    def test_interpolation_saturation_and_opposite_sign_conventions(self):
        table = tuple(i * 100.0 for i in range(26))
        wheel = WheelCurveInput(4.5/180, 0, 4000, 1)
        self.assertEqual(wheel_response(table, 0, wheel), -450)
        self.assertEqual(wheel_response(table, 0, wheel, secondary=True), 450)
        for slip in (25/180, 1.0):
            self.assertEqual(wheel_response(table, 0, WheelCurveInput(slip, 0, 4000, 1)), -2500)

    def test_load_branches_and_secondary_ignores_global_switch(self):
        table = (100.0,) * 26
        wheel = WheelCurveInput(0, 0, 30000, 1)
        self.assertEqual(wheel_response(table, 0, wheel), 100)
        self.assertGreater(wheel_response(table, 0, wheel, alternate_load=True), 100)
        self.assertEqual(wheel_response(table, 0, wheel, secondary=True), 500)
        self.assertEqual(wheel_response(table, 0, wheel, secondary=True, alternate_load=True), 500)

    def test_zero_slip_retains_angle_term_and_surface_scaling(self):
        wheel = WheelCurveInput(0, 0.01, 4000, 0.5)
        primary = wheel_response((0,) * 26, 0.1, wheel)
        secondary = wheel_response((0,) * 26, 0.1, wheel, secondary=True)
        self.assertAlmostEqual(primary, 360, places=4)
        self.assertAlmostEqual(secondary, primary * f32(0.15), places=4)
        self.assertEqual(wheel_response((100,) * 26, 1, WheelCurveInput(1, 1, 0, 1)), 0)

    def test_invalid_observations(self):
        valid = WheelCurveInput(0, 0, 1000, 1)
        for table in ((1,) * 25, (math.nan,) * 26, (1e100,) * 26):
            with self.assertRaises(ValueError):
                wheel_response(table, 0, valid)
        for field in ('slip_angle', 'secondary_angle', 'normal_load', 'surface_multiplier'):
            values = dict(vars(valid), **{field: math.inf})
            with self.assertRaises(ValueError):
                wheel_response((1,) * 26, 0, WheelCurveInput(**values))
        with self.assertRaises(ValueError):
            wheel_response((1,) * 26, 0, WheelCurveInput(0, 0, -1, 1))


if __name__ == '__main__':
    unittest.main()
