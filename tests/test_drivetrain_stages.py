from dataclasses import replace
import unittest

from client.drivetrain_stages import (update_clutch, prepare_drive,
    accumulate_drive_request, distribute_drive, apply_drive_forces)
from client.driving_mode import vehicle_control_mode
from tools.drivetrain_stages_oracle import base


class DrivetrainStagesTests(unittest.TestCase):
    def test_clutch_release_and_damage_change_engagement(self):
        s,c=base()
        released=update_clutch(replace(s,override_byte=1),c)
        self.assertLess(released.engagement,s.engagement)
        slow=update_clutch(replace(s,coupling_resistance=201),c)
        damaged=update_clutch(replace(s,coupling_resistance=201,damage_one=.5),c)
        self.assertGreater(damaged.engagement,slow.engagement)
        self.assertGreater(slow.clutch_gain,slow.engagement)
        self.assertEqual(s.engagement,.5)  # Caller state remains unchanged.

    def test_missing_driven_contact_preserves_previous_speed(self):
        s,c=base();s.driven_speed=123
        s.wheels=[replace(w,contact=False) for w in s.wheels]
        out=prepare_drive(s,c)
        self.assertEqual(out.driven_speed,123)
        self.assertNotEqual(out.previous_rotation,s.previous_rotation)
        self.assertEqual(prepare_drive(replace(s,acceleration=1000),c).wheel_acceleration,100)

    def test_request_threshold_mode_and_saturation(self):
        s,c=base()
        self.assertEqual(accumulate_drive_request(replace(s,alternate_speed=2.5),c).request,0)
        ordinary=accumulate_drive_request(s,c).request
        self.assertGreater(accumulate_drive_request(replace(s,component_mode=5),c).request,ordinary)
        self.assertEqual(accumulate_drive_request(replace(s,request=1),c).request,1)

    def test_neutral_and_signed_hold_counter(self):
        s,c=base();calls=[]
        execute=lambda *args:calls.append(args)
        self.assertEqual(distribute_drive(replace(s,gear=1),c,execute).output_torque,0)
        for hold in (1,-1):
            out=distribute_drive(replace(s,hold_ticks=hold),c,execute)
            self.assertEqual((out.output_torque,out.hold_ticks),(0,hold-1))
        self.assertEqual(calls,[])

    def test_damage_delivery_precedes_damage_field_consumption(self):
        s,c=base();s.effective_torque=1000;s.clutch_gain=1;s.drag_speed=0
        calls=[]
        def effect(call,current):
            calls.append((call.stage,call.code))
            if call.stage=='damage':current.damage_one=.75
        damaged=distribute_drive(s,c,effect)
        baseline=distribute_drive(s,c,lambda *args:None)
        self.assertEqual(calls,[('damage',13),('effect',25)])
        self.assertLess(damaged.output_torque,baseline.output_torque)

    def test_final_stop_flag_and_per_wheel_query(self):
        s,c=base();s.raw_throttle=0;s.speed=0
        stopped=distribute_drive(s,c,lambda *args:None)
        calls=[]
        out=apply_drive_forces(stopped,c,lambda *args:calls.append(args))
        self.assertEqual(calls,[])
        self.assertTrue(all(w.spin==0 for w in out.wheels))
        def gate(call,current):calls.append(call.stage);return True
        apply_drive_forces(s,c,gate)
        self.assertEqual(calls,['vehicle_gate']*4)

    def test_reverse_force_and_unloaded_wheel(self):
        s,c=base();s.longitudinal_speed=0;s.wheel_acceleration=0
        s.wheels=[replace(w,longitudinal_force=0,normal_load=0 if i==1 else 1000)
                  for i,w in enumerate(s.wheels)]
        forward=apply_drive_forces(s,c,lambda *args:True)
        reverse=apply_drive_forces(replace(s,gear=0),c,lambda *args:True)
        self.assertEqual(forward.wheels[1].longitudinal_force,0)
        self.assertGreater(forward.wheels[0].longitudinal_force,0)
        self.assertEqual(reverse.wheels[0].longitudinal_force,-forward.wheels[0].longitudinal_force)
        with self.assertRaisesRegex(ValueError,'boolean vehicle gate'):
            apply_drive_forces(s,c,lambda *args:1)

    def test_mode_flags_and_local_identity_are_independent(self):
        for flag in (2,0x10,0x200):
            self.assertEqual(vehicle_control_mode(flag,False,0),1)
        self.assertEqual(vehicle_control_mode(4,True,3),3)
        self.assertEqual(vehicle_control_mode(4,False,3),0)
        with self.assertRaises(ValueError):vehicle_control_mode(4,1,3)

    def test_configuration_integer_width_matches_native_api(self):
        s,c=base()
        for changes in ({'clutch_steps':0x80000000},{'maximum_rpm':True},
                        {'option_kind':.5},{'secondary_kind':0x80000000}):
            with self.assertRaises(ValueError):update_clutch(s,replace(c,**changes))


if __name__=='__main__':unittest.main()
