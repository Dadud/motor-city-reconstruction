from dataclasses import replace
import unittest
from client.brake_forces import update_brake_forces
from tools.brake_forces_oracle import cases


class BrakeForceTests(unittest.TestCase):
    def state(self):
        s=next(cases())
        t=replace(s.thermal,speed=20,service_control=1,parking_control=False,
            front=replace(s.thermal.front,temperature=100),rear=replace(s.thermal.rear,temperature=100))
        wheels=tuple(replace(w,normal_load=4000,projected_speed=20,spin_value=3,
            spin_adjustment=0,longitudinal_force=0,control_angle=0) for w in s.wheels)
        return replace(s,thermal=t,wheels=wheels,front_gate=0,rear_gate=0,auxiliary_flag=False,parking_ramp=0)

    def test_no_control_clears_previous_force_without_spin_changes(self):
        s=self.state();s=replace(s,thermal=replace(s.thermal,service_control=0))
        out=update_brake_forces(s)
        self.assertEqual(tuple(w.brake_force for w in out.state.thermal.wheels),(0,)*4)
        self.assertEqual(tuple(w.spin_adjustment for w in out.state.wheels),(0,)*4)
        self.assertEqual(out.wear_events,())

    def test_service_opposes_forward_and_reverse_motion(self):
        s=self.state();out=update_brake_forces(s).state
        self.assertTrue(all(w.longitudinal_force<0 for w in out.wheels))
        self.assertTrue(all(w.spin_adjustment<0 for w in out.wheels))
        reverse=replace(s,wheels=tuple(replace(w,projected_speed=-20,spin_value=-3) for w in s.wheels))
        out=update_brake_forces(reverse).state
        self.assertTrue(all(w.longitudinal_force>0 for w in out.wheels))
        self.assertTrue(all(w.spin_adjustment>0 for w in out.wheels))

    def test_parking_ramp_updates_per_rear_wheel(self):
        s=self.state();s=replace(s,parking_ramp=60,thermal=replace(s.thermal,service_control=0,parking_control=True))
        out=update_brake_forces(s).state
        self.assertEqual(out.parking_ramp,64)
        self.assertEqual(out.wheels[0].longitudinal_force,0)
        self.assertLess(out.wheels[2].longitudinal_force,0)

    def test_pair_gate_does_not_roll_back_earlier_wheel(self):
        s=self.state();wheels=list(s.wheels);wheels[1]=replace(wheels[1],control_angle=-.4)
        out=update_brake_forces(replace(s,wheels=tuple(wheels),front_gate=1)).state
        self.assertLess(out.wheels[0].spin_adjustment,0)
        self.assertEqual(out.wheels[1].spin_adjustment,0)

    def test_low_speed_force_and_load_gate(self):
        s=self.state();wheels=tuple(replace(w,projected_speed=.5,normal_load=0 if i==0 else 4000) for i,w in enumerate(s.wheels))
        out=update_brake_forces(replace(s,wheels=wheels,thermal=replace(s.thermal,speed=.5))).state
        self.assertEqual(out.wheels[0].longitudinal_force,0)
        self.assertEqual(out.wheels[1].longitudinal_force,-.5*s.thermal.mass_parameter*8)

    def test_wear_is_ordered_and_rejects_invalid_ramp(self):
        s=self.state();t=replace(s.thermal,front=replace(s.thermal.front,temperature=900),
                               rear=replace(s.thermal.rear,temperature=900))
        out=update_brake_forces(replace(s,thermal=t))
        self.assertEqual(tuple(slot for slot,_ in out.wear_events),(0,1,2,3))
        self.assertTrue(all(amount>0 for _,amount in out.wear_events))
        with self.assertRaises(ValueError):update_brake_forces(replace(s,parking_ramp=-1))
