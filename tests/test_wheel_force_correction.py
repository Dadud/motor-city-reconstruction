import unittest
from dataclasses import replace

from client.wheel_force_correction import ForceCorrectionWheel, correct_wheel_forces
from client.tire_response import f32


class WheelForceCorrectionTests(unittest.TestCase):
    def wheel(self, **values):
        return replace(ForceCorrectionWheel(10, 20, 3, .5, 0, 0, 2000, 1, .8, True, False), **values)

    def run_case(self, wheel, service=0, other=0, parking=False, direction=1, override=False):
        return correct_wheel_forces((wheel,)*4, service, other, parking, direction, override)

    def test_unloaded_decay_requires_zero_longitudinal_force(self):
        free=self.wheel(contact=False)
        self.assertEqual(self.run_case(free)[0].spin_value, f32(20*f32(.999375)))
        held=self.wheel(contact=False,longitudinal_force=1)
        self.assertEqual(self.run_case(held)[0].spin_value,20)
        self.assertEqual(self.run_case(free)[0].spin_adjustment,3)

    def test_contact_matching_spin_removes_previous_adjustment(self):
        result=self.run_case(self.wheel())
        self.assertEqual(result[0].spin_adjustment,0)
        self.assertEqual(result[0].spin_value,20)

    def test_parking_observation_only_changes_rear_pair(self):
        wheel=self.wheel(projected_speed=0,longitudinal_force=-1000)
        result=self.run_case(wheel,parking=True)
        self.assertEqual(result[0].spin_adjustment,result[1].spin_adjustment)
        self.assertEqual(result[2].spin_adjustment,result[3].spin_adjustment)
        self.assertGreater(result[2].spin_adjustment,result[0].spin_adjustment)

    def test_direction_clamp_override(self):
        wheel=self.wheel(projected_speed=-30,correction_enabled=True)
        limited=self.run_case(wheel,direction=2)[0]
        unlimited=self.run_case(wheel,direction=2,override=True)[0]
        self.assertGreater(limited.spin_adjustment,unlimited.spin_adjustment)

    def test_invalid_scale_rejected(self):
        with self.assertRaises(ValueError): self.run_case(self.wheel(spin_scale=0))


if __name__ == '__main__': unittest.main()
