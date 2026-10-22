import unittest
from dataclasses import replace
import struct
from client.tire_update import TireCurves, update_tires
from tools.tire_update_oracle import cases


class TireUpdateTests(unittest.TestCase):
    def test_curves_are_bound_from_native_front_and_rear_configuration_slots(self):
        image = bytearray(0x820)
        for axle, base, scale in (('front', 0x148, 1), ('rear', 0x24c, 2)):
            struct.pack_into('<f', image, base, .01 * scale)
            struct.pack_into('<26f', image, base + 8,
                             0., *(scale * i for i in range(1, 26)))
            struct.pack_into('<26f', image, base + 0x70,
                             0., *(-scale * i for i in range(1, 26)))
            curves = TireCurves.from_assembled_configuration(image, axle)
            self.assertEqual(curves.primary, (0., *(scale * i for i in range(1, 26))))
            self.assertEqual(curves.secondary, (0., *(-scale * i for i in range(1, 26))))
            self.assertAlmostEqual(curves.angle_coefficient, .01 * scale, places=7)

    def test_curve_binding_rejects_invalid_assembly_shape_or_values(self):
        with self.assertRaisesRegex(ValueError, '0x820-byte'):
            TireCurves.from_assembled_configuration(bytes(8), 'front')
        with self.assertRaisesRegex(ValueError, 'axle'):
            TireCurves.from_assembled_configuration(bytes(0x820), 'left')
        image = bytearray(0x820)
        struct.pack_into('<f', image, 0x148, float('nan'))
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            TireCurves.from_assembled_configuration(image, 'front')

    def state(self, **values):
        state = next(cases())
        wheels = tuple(replace(w, normal_load=4000, contact=True, projected_speed=20) for w in state.wheels)
        return replace(state, wheels=wheels, speed=20, longitudinal_velocity=20,
                       lateral_velocity=.25, yaw_rate=0, body_slip=0, raw_control=0,
                       mode_observations=(True,)*4, **values)

    def test_stationary_stabilization_and_contact_gate(self):
        state = replace(self.state(), speed=0, lateral_velocity=.2, yaw_rate=.3)
        wheels = tuple(replace(w, contact=(i%2==0)) for i,w in enumerate(state.wheels))
        out = update_tires(replace(state,wheels=wheels))
        self.assertEqual(out.lateral_velocity,0)
        self.assertAlmostEqual(out.yaw_rate,.285,places=6)
        self.assertLess(out.lateral_acceleration,0)
        for i,w in enumerate(out.wheels):
            self.assertEqual(w.secondary_response,0)
            if i%2:
                self.assertEqual((w.lateral_force,w.longitudinal_force),(0,0))
            else:
                self.assertLess(w.lateral_force,0)
                self.assertEqual(w.longitudinal_force,state.wheels[i].longitudinal_force)

    def test_exact_quarter_speed_uses_curves_after_stabilization(self):
        state=replace(self.state(),speed=.25,lateral_velocity=.2)
        out=update_tires(state)
        self.assertEqual(out.lateral_velocity,0)
        no_initial_drift=update_tires(replace(state,lateral_velocity=0))
        self.assertEqual(out.wheels[0].lateral_force,no_initial_drift.wheels[0].lateral_force)
        self.assertNotEqual(out.wheels[0].lateral_force,update_tires(replace(state,speed=.24999)).wheels[0].lateral_force)

    def test_reverse_changes_steering_slip_sign(self):
        state=replace(self.state(),raw_control=127,maximum_steering=.08)
        forward=update_tires(state)
        reverse=update_tires(replace(state,wheels=tuple(replace(w,projected_speed=-20) for w in state.wheels)))
        for a,b in zip(forward.wheels,reverse.wheels):
            self.assertEqual(a.slip_angle,-b.slip_angle)
        self.assertNotEqual(forward.wheels[0].steering_angle,forward.wheels[1].steering_angle)

    def test_rear_steering_changes_direction_across_speed_gate(self):
        state=replace(self.state(),raw_control=127,rear_steering=True,maximum_steering=.08)
        self.assertLess(update_tires(replace(state,speed=8)).wheels[2].steering_angle,0)
        self.assertGreater(update_tires(replace(state,speed=10)).wheels[2].steering_angle,0)

    def test_per_wheel_mode_observations_are_independent(self):
        state=replace(self.state(),body_slip=.02,mode_observations=(True,False,True,False))
        self.assertEqual(tuple(w.slip_angle!=0 for w in update_tires(state).wheels),state.mode_observations)

    def test_invalid_record_and_observation_counts(self):
        state=self.state()
        for invalid in (replace(state,wheels=state.wheels[:3]),replace(state,mode_observations=(True,)),
                        replace(state,wheelbase=0)):
            with self.assertRaises(ValueError):
                update_tires(invalid)
