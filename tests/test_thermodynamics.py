from dataclasses import astuple, replace
import unittest

from client.dyno_solver import cylinder_geometry
from client.thermodynamics import initial_cylinder_state


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
