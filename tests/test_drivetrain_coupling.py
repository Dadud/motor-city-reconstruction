from dataclasses import replace
import unittest
from client.drivetrain_coupling import DrivetrainCoupling, couple_drivetrain, environment_correction


class DrivetrainCouplingTests(unittest.TestCase):
    def setUp(self):
        self.state=DrivetrainCoupling(3000,250,200,2,30,2,.5,12,0,False,False,0)

    def test_neutral_bypasses_engagement_and_resistance(self):
        out=couple_drivetrain(replace(self.state,gear_index=1,engagement=1))
        self.assertEqual(out.acceleration_input,out.corrected_torque)

    def test_full_engagement_removes_positive_drive_acceleration(self):
        out=couple_drivetrain(replace(self.state,engagement=1))
        self.assertEqual(out.acceleration_input,-12)
        braking=couple_drivetrain(replace(self.state,engagement=1,effective_torque=-200))
        self.assertLess(braking.acceleration_input,braking.corrected_torque)

    def test_zero_engagement_bypasses_resistance(self):
        out=couple_drivetrain(replace(self.state,engagement=0))
        self.assertEqual(out.acceleration_input,out.corrected_torque)

    def test_negative_power_is_clamped_but_torque_keeps_sign(self):
        out=couple_drivetrain(replace(self.state,curve_torque=-250,effective_torque=-200))
        self.assertEqual(out.power,0)
        self.assertLess(out.corrected_torque,0)

    def test_environment_selector_requires_enable(self):
        self.assertEqual(environment_correction(0,False,False,1),environment_correction(0,False,False,2))
        self.assertGreater(environment_correction(0,False,True,2),environment_correction(0,False,True,1))

    def test_nonfinite_engagement_is_rejected(self):
        with self.assertRaises(ValueError): couple_drivetrain(replace(self.state,engagement=float('nan')))
