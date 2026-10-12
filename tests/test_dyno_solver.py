import unittest
import struct

from client.dyno_solver import (CamProfile, airflow_area, cam_profiles, cylinder_geometry,
                                flow_coefficients, mechanical_loss, rpm_work_factor,
                                interpolate_flow, pressure_correct_flow,
                                valve_events, valve_lift, work_outputs)


class DynoSolverTests(unittest.TestCase):
    def test_airflow_area_native_coupling(self):
        points = (.1, .2, .3, .4, .5, .6, .7, .8, 0, 0)
        coefficients = (.9, .8, .7, .6, .5, .4, .3, .2, 0, 0)
        self.assertEqual(airflow_area(.35, points, coefficients, 1.6),
                         1.1435397863388062)
        self.assertEqual(airflow_area(.35, points, coefficients, 1.6,
                                     pressure_ratio=2), 1.3937615156173706)
        self.assertEqual(airflow_area(0, points, coefficients, 1.6), 0)
        with self.assertRaises(ValueError):
            airflow_area(.35, points, coefficients, 0)

    def test_pressure_correction_native_reference(self):
        self.assertEqual(pressure_correct_flow(.6, 1.5), 0.6783962366628759)
        self.assertEqual(pressure_correct_flow(.6, 2), 0.748755519787138)
        self.assertEqual(pressure_correct_flow(.6, 1.8929), 0.4300000071525574)
        self.assertEqual(pressure_correct_flow(.6, 1), .6)
        self.assertEqual(pressure_correct_flow(1.2, 1), 1)
        self.assertEqual(pressure_correct_flow(-.2, 1), 0.4300000071525574)
        for ratio in (-1, float('nan')):
            with self.assertRaises(ValueError):
                pressure_correct_flow(.6, ratio)

    def test_flow_interpolation_native_reference(self):
        points = (.1, .2, .3, .4, .5, .6, .7, .8, 0, 0)
        coefficients = (.9, .8, .7, .6, .5, .4, .3, .2, 0, 0)
        for lift, expected in ((0, 1), (.05, .9499999888241293),
                               (.2, .8000000149011601),
                               (.35, .6500000149011586),
                               (.75, .2500000074505806),
                               (1, 4.470347469975877e-8)):
            self.assertEqual(interpolate_flow(lift, points, coefficients), expected)

    def test_flow_interpolation_invalid_inputs(self):
        for lift, points, values in ((0, (1,)*9, (1,)*10),
                                     (float('nan'), (1,)*10, (1,)*10),
                                     (-1, (1,)*10, (1,)*10),
                                     (0, (0,)*10, (1,)*10),
                                     (2, (1,)*10, (1,)*10)):
            with self.assertRaises(ValueError):
                interpolate_flow(lift, points, values)

    def test_valve_lift_native_branch_samples(self):
        profile = CamProfile(1.5, 19.16698455810547, 59, 98.83301544189453,
                             0.22916758060455322, 0.48676931858062744)
        for angle, expected in ((144, 0.005420728423410626),
                                (234, 0.23943589794001052),
                                (334, 0.06972096818792212)):
            self.assertEqual(valve_lift(profile, 134, 370, angle), expected)

    def test_valve_lift_window_and_exact_phase_boundaries(self):
        profile = CamProfile(1.5, 20, 60, 100, .2, .5)
        for angle in (99, 100, 140, 300, 340, 341):
            self.assertEqual(valve_lift(profile, 100, 340, angle), 0)
        self.assertGreater(valve_lift(profile, 100, 340, 200), 0)
        with self.assertRaises(ValueError):
            valve_lift(profile, 100, 340, float('nan'))

    def test_cam_profile_native_reference(self):
        from dataclasses import astuple
        data = bytearray(1004)
        struct.pack_into('<6f', data, 0xa8, 66, 10, 12, 62,
                         0.2614174485206604, 0.24842533469200134)
        struct.pack_into('<h', data, 0x84, 1)
        profiles = cam_profiles(bytes(data))
        self.assertEqual(tuple(astuple(p) for p in profiles),
                         ((1.5, 19.16698455810547, 59.0, 98.83301544189453,
                           0.22916758060455322, 0.48676931858062744),
                          (1.5, 18.544214248657227, 63.5, 108.4557876586914,
                           0.2971295118331909, 0.42746883630752563)))
        struct.pack_into('<f', data, 0xb8, float('nan'))
        with self.assertRaises(ValueError):
            cam_profiles(bytes(data))

    def test_flow_coefficients_native_synthetic_reference(self):
        data = bytearray(1004)
        for offset in (0x314, 0x318, 0x31c, 0x320):
            struct.pack_into('<f', data, offset, 1)
        for offset in (0x374, 0x39c, 0x324, 0x34c):
            struct.pack_into('<10f', data, offset, *([1]*10))
        result = flow_coefficients(bytes(data))
        self.assertEqual(result.scalar_314, 1060.8341064453125)
        self.assertEqual(result.series_374, (0.011311853304505348,)*10)
        self.assertEqual(result.series_324, (0.011311853304505348,)*10)
        # Native skip branches retain zero for nonpositive flow numerators.
        struct.pack_into('<f', data, 0x374, -1)
        struct.pack_into('<f', data, 0x324, 0)
        struct.pack_into('<f', data, 0x39c, 0)
        struct.pack_into('<f', data, 0x34c, 0)
        result = flow_coefficients(bytes(data))
        self.assertEqual((result.series_374[0], result.series_324[0]), (0, 0))
        struct.pack_into('<f', data, 0x374, 1)
        with self.assertRaises(ValueError):
            flow_coefficients(bytes(data))

    def test_valve_events_adjustment_and_sizes(self):
        data = bytearray(1004)
        for offset, value in ((0xa8, 66), (0xac, 10), (0xb0, 12),
                              (0xb4, 62), (0x98, 1.5), (0x9c, 1.25)):
            struct.pack_into('<f', data, offset, value)
        struct.pack_into('<h', data, 0xc0, 20)
        struct.pack_into('<h', data, 0x310, 2)
        struct.pack_into('<h', data, 0x312, 1)
        for train, adjustment in ((1, 28.5), (2, 20.5), (3, 17)):
            struct.pack_into('<h', data, 0x84, train)
            for flag in (0, 1):
                struct.pack_into('<h', data, 0x82, flag)
                events = valve_events(bytes(data))
                delta = adjustment if flag else 0
                self.assertEqual(events.angle_b0, 328-delta)
                self.assertEqual(events.angle_b4, 582+delta)
                self.assertEqual(events.angle_a8, 114-delta)
                self.assertEqual(events.angle_ac, 350+delta)
                self.assertEqual((events.intake_size, events.exhaust_size), (3, 1.25))

    def test_valve_events_reject_malformed_records(self):
        for data in (bytes(10), bytearray(1004)):
            with self.assertRaises(ValueError):
                valve_events(data)
        data = bytearray(1004)
        struct.pack_into('<f', data, 0xa8, float('nan'))
        with self.assertRaises(ValueError):
            valve_events(bytes(data))

    def test_cylinder_geometry_native_reference(self):
        from dataclasses import astuple
        geometry = cylinder_geometry(3.0625998973846436, 3.750001907348633,
                                     6.150000095367432, 8)
        self.assertEqual(astuple(geometry),
                         (9.379518508911133, 14.725844383239746,
                          27.624977111816406, 5.364073276519775,
                          6.075003147125244, 220.99981689453125))

    def test_invalid_cylinder_geometry(self):
        for bore, stroke, compression, cylinders in (
                (0, 3, 8, 8), (3, 0, 8, 8), (3, 3, 1, 8),
                (3, 3, 8, True), (float('nan'), 3, 8, 8)):
            with self.assertRaises(ValueError):
                cylinder_geometry(bore, stroke, compression, cylinders)

    def test_mechanical_loss_reference_knots(self):
        # CPU-emulated solver outputs, including native float32 stroke input.
        stroke = 3.750001907348633
        self.assertEqual(mechanical_loss(2000, stroke), 17.796566009521484)
        self.assertEqual(mechanical_loss(11000, stroke), 64.86393737792969)

    def test_rejects_interpolated_or_invalid_inputs(self):
        for rpm in (True, 2000.0, 2250, 11500):
            with self.assertRaises(ValueError):
                mechanical_loss(rpm, 3.75)
            with self.assertRaises(ValueError):
                rpm_work_factor(rpm)
        for stroke in (0, -1, float('nan'), float('inf'), 6):
            with self.assertRaises(ValueError):
                mechanical_loss(2000, stroke)

    def test_rpm_factors(self):
        self.assertGreater(rpm_work_factor(2000), rpm_work_factor(2500))
        self.assertEqual(rpm_work_factor(4000), rpm_work_factor(11000))

    def test_work_stage_native_reference(self):
        self.assertEqual(work_outputs(2000, 3.750001907348633,
                         2972.227294921875, 27.624977111816406,
                         441999.625, 0, 0),
                         (58.325347900390625, 153.10403442382812,
                          142.8277587890625, 105.9586410522461,
                          17.796566009521484))

    def test_negative_power_clamps_after_work_calculation(self):
        power, torque, loss, work, mechanical = work_outputs(
            2000, 3.75, 0, 30, 400000, 0, 0)
        self.assertEqual((power, torque), (0, 0))
        self.assertLess(work, 0)
        self.assertLess(loss, 0)
        self.assertGreater(mechanical, 0)

    def test_invalid_work_geometry(self):
        for volume, rate in ((0, 400000), (30, 0), (float('nan'), 400000)):
            with self.assertRaises(ValueError):
                work_outputs(2000, 3.75, 0, volume, rate, 0, 0)


if __name__ == '__main__':
    unittest.main()
