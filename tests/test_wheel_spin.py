from dataclasses import replace
import unittest
from client.wheel_spin import integrate_wheel_spin
from tools.wheel_spin_oracle import cases


class WheelSpinTests(unittest.TestCase):
    def state(self):
        s=next(cases())
        wheels=tuple(replace(w,spin_value=1,spin_adjustment=32,normal_load=0,correction_enabled=True,
            contact=False,projected_speed=0) for w in s.wheels)
        return replace(s,wheels=wheels,direction_mode=1)

    def test_integration_and_zero_speed_slip(self):
        out=integrate_wheel_spin(self.state()).state
        self.assertEqual(tuple(w.spin_value for w in out.wheels),(2,)*4)
        self.assertEqual(tuple(w.slip_ratio for w in out.wheels),(0,)*4)
        self.assertTrue(all(w.local_vertical==0 for w in out.wheels))

    def test_driven_limit_and_override(self):
        s=replace(self.state(),direction_mode=0,rpm=0)
        self.assertEqual(tuple(w.spin_value for w in integrate_wheel_spin(s).state.wheels),(0,)*4)
        self.assertEqual(tuple(w.spin_value for w in integrate_wheel_spin(replace(s,override_control=True)).state.wheels),(2,)*4)

    def test_contact_changes_secondary_angle(self):
        s=self.state();airborne=integrate_wheel_spin(s).state
        ground=integrate_wheel_spin(replace(s,wheels=tuple(replace(w,contact=True) for w in s.wheels))).state
        self.assertGreater(ground.wheels[0].secondary_angle,airborne.wheels[0].secondary_angle)
        self.assertTrue(all(abs(w.secondary_angle)<=.08333334 for w in ground.wheels))

    def test_front_and_rear_lateral_motion_and_event_order(self):
        s=self.state();wheels=tuple(replace(w,spin_value=30,spin_adjustment=0) for w in s.wheels)
        out=integrate_wheel_spin(replace(s,wheels=wheels))
        self.assertGreater(out.state.wheels[0].local_lateral,out.state.wheels[2].local_lateral)
        self.assertEqual(tuple(slot for slot,_ in out.wear_events),(0,1,2,3))

    def test_invalid_inputs(self):
        s=self.state()
        for invalid in (replace(s,direction_mode=256),replace(s,wheels=s.wheels[:3]),replace(s,front_scale=0)):
            with self.assertRaises(ValueError):integrate_wheel_spin(invalid)
