from dataclasses import astuple, replace
import unittest

from client.dyno_solver import cylinder_geometry
from client.thermodynamics import (charge_temperature, cycle_preparation,
                                   exhaust_parameters, exhaust_phase_factor,
                                   exhaust_wave_value, initial_cylinder_state,
                                   intake_boundary)


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


class CyclePreparationTests(unittest.TestCase):
    def test_native_intake_boundary_and_post_store_boost(self):
        geometry = cylinder_geometry(4, 3.5, 9, 8)
        self.assertEqual(astuple(intake_boundary(geometry, 2000, 300, 2, 1)),
                         (703716.8125, 2370.384765625, 14.35813045501709))
        self.assertEqual(intake_boundary(geometry, 2000, 300, 2, 1, 5).pressure,
                         19.358131408691406)

    def test_native_negative_intake_boundary_is_preserved(self):
        geometry = cylinder_geometry(4, 3.5, 9, 8)
        self.assertEqual(astuple(intake_boundary(geometry, 11000, 300, 2, 4)),
                         (3870442.5, 592.59619140625, -150.7646942138672))

    def test_invalid_intake_boundary(self):
        geometry = cylinder_geometry(4, 3.5, 9, 8)
        for inputs in ((geometry, 0, 300, 2, 1), (geometry, 2000, 299, 2, 1),
                       (geometry, 2000, 300, 3, 1), (geometry, 2000, 300, 2, 0),
                       (None, 2000, 300, 2, 1)):
            with self.assertRaises(ValueError):
                intake_boundary(*inputs)

    def test_temperature_mode_and_thresholds(self):
        self.assertEqual(charge_temperature(1, 2000), 584.5599975585938)
        self.assertEqual(charge_temperature(1, 5500), 540)
        self.assertEqual(charge_temperature(10, 2000), 540)
        self.assertEqual(charge_temperature(19, 2000), 540)
        self.assertEqual(charge_temperature(20, 5500), 560.0399780273438)
        self.assertEqual(charge_temperature(20, 6000), 560)

    def test_native_coupled_preparation_and_wave(self):
        exhaust = exhaust_parameters(1, 2000, 1)
        prepared = cycle_preparation(2000, charge_temperature(1, 2000), exhaust)
        self.assertEqual(astuple(prepared), (139.1498565673828, 12, 4.207139492034912))
        factor = exhaust_phase_factor(60)
        self.assertEqual(factor, .8999999761581421)
        self.assertEqual(exhaust_wave_value(120, 60, factor, 2000, exhaust,
                                           prepared.exhaust_wave_scale), 43.00245666503906)
        self.assertEqual(exhaust_wave_value(270, 60, factor, 2000, exhaust,
                                           prepared.exhaust_wave_scale), 36.040061950683594)

    def test_exact_wave_boundaries_retain_previous_value(self):
        exhaust = exhaust_parameters(1, 4000, 1)
        for angle in (180, 360):
            self.assertEqual(exhaust_wave_value(angle, 0, 1, 4000, exhaust, 10, 12.34),
                             12.34000015258789)
        self.assertNotEqual(exhaust_wave_value(179.9999, 0, 1, 4000, exhaust, 10, 12.34),
                            12.34000015258789)
        self.assertNotEqual(exhaust_wave_value(360.0001, 0, 1, 4000, exhaust, 10, 12.34),
                            12.34000015258789)

    def test_boost_overrides_wave_and_retained_boundary(self):
        exhaust = exhaust_parameters(1, 4000, 1)
        self.assertEqual(exhaust_wave_value(180, 0, 1, 4000, exhaust, 10, 12.34, boost=1),
                         30.33333396911621)

    def test_invalid_cycle_inputs(self):
        for mode, rpm in ((0, 2000), (True, 2000), (1, 0), (1, float('nan'))):
            with self.assertRaises(ValueError):
                charge_temperature(mode, rpm)
        for angle in (360, 720, float('inf')):
            with self.assertRaises(ValueError):
                exhaust_phase_factor(angle)
        exhaust = exhaust_parameters(1, 2000, 1)
        for rpm, temperature, parameters in ((2000, 0, exhaust), (0, 540, exhaust),
                                             (2000, 540, None), (2000, 1e300, exhaust)):
            with self.assertRaises(ValueError):
                cycle_preparation(rpm, temperature, parameters)
        with self.assertRaises(ValueError):
            exhaust_wave_value(90, 0, 0, 2000, exhaust, 10)
