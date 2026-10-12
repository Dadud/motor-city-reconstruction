from dataclasses import astuple, replace
import unittest

from client.dyno_solver import cylinder_geometry
from client.thermodynamics import exhaust_parameters, initial_cylinder_state


class CylinderStateTests(unittest.TestCase):
    def setUp(self):
        self.geometry = cylinder_geometry(4, 3.5, 9, 8)

    def test_native_reference(self):
        self.assertEqual(astuple(initial_cylinder_state(self.geometry, 3.5, 120)),
                         (44.099998474121094, 2000.0, 1.75,
                          3.240000009536743, 12.566370964050293,
                          0.0014148541959002614, 0.0017898220103234053))

    def test_pressure_changes_mass_but_not_geometry(self):
        low = initial_cylinder_state(self.geometry, 3.5, 120, 15)
        high = initial_cylinder_state(self.geometry, 3.5, 120, 80)
        self.assertGreater(high.mass_term, low.mass_term)
        self.assertEqual(high.reference_mass_term, low.reference_mass_term)
        self.assertEqual(high.piston_area, low.piston_area)

    def test_invalid_state(self):
        for stroke, angle, pressure in ((0, 120, 44.1), (6, 120, 44.1),
                                        (3.5, float('nan'), 44.1),
                                        (3.5, 120, 0)):
            with self.assertRaises(ValueError):
                initial_cylinder_state(self.geometry, stroke, angle, pressure)
        with self.assertRaises(ValueError):
            initial_cylinder_state(replace(self.geometry, rod_length=.1), 3.5, 90)
        with self.assertRaises(ValueError):
            initial_cylinder_state(None, 3.5, 120)


class ExhaustTests(unittest.TestCase):
    def test_native_mode_seven_transition(self):
        self.assertEqual(astuple(exhaust_parameters(7, 2000, 1)),
                         (26.25, .5, 6000, .949999988079071))
        self.assertEqual(exhaust_parameters(7, 5500, 1).baseline, 21)
        self.assertEqual(exhaust_parameters(7, 11000, 1).baseline, 21)

    def test_native_mode_constants(self):
        self.assertEqual(astuple(exhaust_parameters(1, 2000, 1)),
                         (35, .30000001192092896, 4000, 1.059999942779541))
        self.assertEqual(exhaust_parameters(4, 2000, 1).rpm_exponent, 1)
        self.assertEqual(exhaust_parameters(6, 2000, 1).baseline, 22.700000762939453)

    def test_invalid_inputs(self):
        for inputs in ((0, 2000, 1), (8, 2000, 1), (True, 2000, 1),
                       (1, 0, 1), (1, 2000, 0), (1, float('nan'), 1),
                       (1, 2000, 1e300)):
            with self.assertRaises(ValueError):
                exhaust_parameters(*inputs)
