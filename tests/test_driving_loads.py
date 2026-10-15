import unittest
from dataclasses import replace
from client.driving_loads import DrivingLoads, LoadParameters
from client.vehicle_update import UpdateCall
from tools.driving_pipeline_oracle import cases


def fixture():
    s, inputs, _ = next(cases())
    s.turning_radius_y = -40.
    s.local_acceleration = (0., 0., 0.)
    for w in s.wheels:
        w.contact = True
    inputs.moments = replace(inputs.moments, wheels=tuple(replace(w, support_correction=9.+i)
        for i, w in enumerate(inputs.moments.wheels)))
    parameters = LoadParameters(1300., 2.7, 1.6, 1.7, .7, 0., 0., -.03,
        100., .45, .55, -2.3, 400., 0, 1.2, .8)
    return s, inputs, parameters


class DrivingLoadsTests(unittest.TestCase):
    def test_normal_load_clears_force_and_maps_rear_record_order(self):
        s, inputs, parameters = fixture()
        loads = DrivingLoads(parameters, lambda *args: None, lambda *args: False)
        loads(UpdateCall('normal_loads'), s, inputs)
        self.assertTrue(all(w.force[0] == 0 and w.force[2] == 0 for w in s.wheels))
        # +0x74 scales are 9/10/11/12 in consecutive owner-record order.
        # Returning a reordered result without reversing its mapping swaps these.
        self.assertGreater(s.wheels[3].force[1], s.wheels[2].force[1])
        self.assertAlmostEqual(s.wheels[3].force[1]/s.wheels[2].force[1], 12/11, places=6)
        self.assertEqual(inputs.moments.mass_parameter, parameters.configuration_mass)
        self.assertEqual(s.mass, 1300.)

    def test_projection_reads_current_controller_and_airborne_spin(self):
        s, inputs, parameters = fixture()
        loads = DrivingLoads(parameters, lambda *args: None, lambda *args: False)
        s.wheels[2].contact = False
        s.wheels[2].spin = 24.; s.wheels[2].spin_scale = .5
        loads(UpdateCall('project_wheels'), s, inputs)
        self.assertEqual(s.wheels[2].projected_speed, 12.)
        s.wheels[2].spin = -18.
        loads(UpdateCall('project_wheels'), s, inputs)
        self.assertEqual(s.wheels[2].projected_speed, -9.)

    def test_resistance_gate_and_unbound_child_are_explicit(self):
        s, inputs, parameters = fixture()
        observations = []
        external = []
        def mode(*args):
            observations.append(True)
            return True
        loads = DrivingLoads(parameters, lambda call, *args: external.append(call.stage), mode)
        original = tuple(w.force for w in s.wheels)
        s.speed = 20.
        loads(UpdateCall('resistance'), s, inputs)
        self.assertEqual(len(observations), 1)
        self.assertEqual(tuple(w.force for w in s.wheels), original)
        s.flags = 0x200
        loads(UpdateCall('resistance'), s, inputs)
        self.assertEqual(len(observations), 1)
        loads(UpdateCall('engine'), s, inputs)
        self.assertEqual(external, ['engine'])
        with self.assertRaises(ValueError):
            DrivingLoads(parameters, None, mode)

    def test_configuration_mass_remains_distinct_and_zero_radius_is_visible(self):
        s, inputs, parameters = fixture()
        s.mass = 999.
        loads = DrivingLoads(parameters, lambda *args: None, lambda *args: False)
        loads(UpdateCall('normal_loads'), s, inputs)
        self.assertEqual(s.mass, 999.)
        self.assertEqual(inputs.moments.mass_parameter, 1300.)
        s.turning_radius_y = 0.
        with self.assertRaises(ValueError):
            loads(UpdateCall('normal_loads'), s, inputs)


if __name__ == '__main__':
    unittest.main()
