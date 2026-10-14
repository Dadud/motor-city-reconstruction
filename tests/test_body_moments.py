from dataclasses import replace
import math
import unittest
from client.body_moments import accumulate_body_moments
from client.wheel_force_orientation import ForceOrientationWheel,orient_wheel_forces
from tools.body_moments_oracle import cases


class BodyMomentTests(unittest.TestCase):
    def state(self):
        s=next(cases())
        return replace(s,wheels=tuple(replace(w,lateral_force=0,longitudinal_force=0,
            secondary_response=0,support_correction=0,contact=True) for w in s.wheels),
            speed=20,front_vertical=0,rear_vertical=0,yaw_contribution=0)

    def test_no_force_and_signed_yaw(self):
        s=self.state()
        self.assertEqual(accumulate_body_moments(s),(0,0,0))
        wheels=list(s.wheels);wheels[0]=replace(wheels[0],lateral_force=100)
        self.assertGreater(accumulate_body_moments(replace(s,wheels=tuple(wheels)))[1],0)
        wheels[0]=replace(wheels[0],lateral_force=-100)
        self.assertLess(accumulate_body_moments(replace(s,wheels=tuple(wheels)))[1],0)

    def test_low_speed_clears_pitch_roll_but_not_yaw(self):
        s=self.state(); wheels=tuple(replace(w,lateral_force=100,support_correction=.2) for w in s.wheels)
        out=accumulate_body_moments(replace(s,wheels=wheels,speed=.49999))
        self.assertEqual((out[0],out[2]),(0,0));self.assertNotEqual(out[1],0)
        self.assertNotEqual(accumulate_body_moments(replace(s,wheels=wheels,speed=.5))[0],0)

    def test_alternate_mode_excludes_differential_longitudinal_moment(self):
        s=self.state(); wheels=list(s.wheels);wheels[0]=replace(wheels[0],longitudinal_force=100)
        normal=accumulate_body_moments(replace(s,wheels=tuple(wheels)))
        alternate=accumulate_body_moments(replace(s,wheels=tuple(wheels),alternate_mode=True))
        self.assertNotEqual(normal[1],0);self.assertEqual(alternate[1],0)
        self.assertEqual(normal[0],alternate[0])

    def test_support_correction_requires_contact(self):
        s=self.state();wheels=tuple(replace(w,support_correction=.2) for w in s.wheels)
        supported=accumulate_body_moments(replace(s,wheels=wheels))
        unsupported=accumulate_body_moments(replace(s,wheels=tuple(replace(w,contact=False) for w in wheels)))
        self.assertGreater(supported[0],0);self.assertGreater(supported[2],0)
        self.assertEqual(unsupported,(0,0,0))

    def test_orientation_keeps_original_asymmetric_formula(self):
        wheels=(ForceOrientationWheel(.25,0,100,200),)*4
        out=orient_wheel_forces(wheels,0,0)
        self.assertAlmostEqual(out[0].lateral_force,-100,places=4)
        self.assertAlmostEqual(out[0].longitudinal_force,-100,places=4)
        self.assertEqual(out[0].steering_angle,.25)

    def test_invalid_data(self):
        s=self.state()
        for invalid in (replace(s,wheels=s.wheels[:3]),replace(s,inverse_pitch=math.nan)):
            with self.assertRaises(ValueError): accumulate_body_moments(invalid)
        with self.assertRaises(ValueError): orient_wheel_forces((),0,0)
