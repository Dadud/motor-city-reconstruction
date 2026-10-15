"""Recovered preparation/support boundary behavior, using authored inputs."""
from dataclasses import replace
import unittest
from client.vehicle_preparation import PreparationState,SupportState,SupportWheel,prepare_vehicle,update_support_disturbance
from tools.vehicle_preparation_oracle import preparation_cases,support_cases
from client.tire_response import f32

class VehiclePreparationTests(unittest.TestCase):
    def test_supported_retains_angles_and_auxiliary(self):
        s=replace(next(preparation_cases()),support_count=2,pitch=.03,roll=-.02,extent=.05)
        out=prepare_vehicle(s)
        self.assertAlmostEqual(out.pitch,.03,places=7)
        self.assertEqual(out.auxiliary,s.auxiliary)
        self.assertEqual(out.angle_delta,(0.,0.,0.))
        self.assertEqual(out.pitch_target,s.pitch_target)

    def test_unsupported_smooths_then_clamps(self):
        s=next(preparation_cases());out=prepare_vehicle(s)
        self.assertEqual(out.auxiliary,(0.,)*6)
        self.assertGreaterEqual(out.pitch,-out.minimum_pitch)
        self.assertLessEqual(out.pitch,out.maximum_pitch)
        self.assertGreaterEqual(out.extent,0)
        self.assertLessEqual(out.extent,max(out.pitch_limit,out.roll_limit))

    def test_damping_direction_and_clamp(self):
        s=PreparationState(front_factor=2,rear_factor=.25)
        self.assertEqual(prepare_vehicle(s).damping,1)
        self.assertEqual(prepare_vehicle(replace(s,local_vertical_acceleration=-1)).damping,0)
        self.assertEqual(prepare_vehicle(replace(s,local_vertical_acceleration=1)).damping,.75)

    def test_inverse_is_transpose(self):
        out=prepare_vehicle(next(preparation_cases()))
        self.assertEqual(out.to_local,tuple(out.to_world[j*3+i] for i in range(3) for j in range(3)))

    def test_repeated_preparation_uses_previous_angles(self):
        first=prepare_vehicle(next(preparation_cases()));second=prepare_vehicle(first)
        self.assertNotEqual(first.angle_delta,second.angle_delta)

    def test_pitch_addition_retains_extended_delta(self):
        s=list(preparation_cases())[-1];out=prepare_vehicle(s)
        self.assertEqual(out.pitch,-.0029866702388972044)
        self.assertNotEqual(out.pitch,f32(f32(s.pitch)+out.angle_delta[0]))

    def test_missing_contact_clears_both_outputs(self):
        out=update_support_disturbance(next(support_cases()))
        self.assertTrue(all(w.displacement==w.correction==0 for w in out.wheels))

    def test_zero_speed_retains_bounded_displacement(self):
        s=replace(next(support_cases()),local_longitudinal_speed=0,
            wheels=tuple(SupportWheel(True,4,.5,1,.9,3) for _ in range(4)),phase=.25)
        out=update_support_disturbance(s)
        self.assertTrue(all(w.correction==0 for w in out.wheels))
        self.assertTrue(all(abs(w.displacement)<=.5 for w in out.wheels))

    def test_support_speed_reversal_changes_displacement_not_correction(self):
        s=replace(next(support_cases()),phase=.125,
            wheels=tuple(SupportWheel(True,4,.5,1,0,0) for _ in range(4)),local_longitudinal_speed=1)
        a=update_support_disturbance(s);b=update_support_disturbance(replace(s,local_longitudinal_speed=-1))
        for wa,wb in zip(a.wheels,b.wheels):
            self.assertEqual(wa.displacement,-wb.displacement)
            self.assertEqual(wa.correction,wb.correction)

    def test_invalid_observations_rejected(self):
        with self.assertRaises(ValueError):prepare_vehicle(PreparationState(support_count=5))
        with self.assertRaises(ValueError):prepare_vehicle(PreparationState(orientation_scale=.5))
        with self.assertRaises(ValueError):update_support_disturbance(replace(next(support_cases()),noise=(0,)))
        with self.assertRaises(ValueError):update_support_disturbance(replace(next(support_cases()),phase=1e20,wheels=tuple(SupportWheel(True,1,1,1) for _ in range(4))))

if __name__=='__main__':unittest.main()
