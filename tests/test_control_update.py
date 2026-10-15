from dataclasses import replace
import unittest
from client.control_update import ControlState,update_controls
from client.tire_response import f32

def supplied(call,state):
    if call.stage=='vehicle_gate':return True
    if call.stage in ('stopped_query','override_query'):return False

class ControlUpdateTests(unittest.TestCase):
    def test_throttle_threshold_and_asymmetric_release(self):
        self.assertEqual(update_controls(ControlState(target_throttle=131,throttle=100),supplied).state.throttle,104)
        self.assertEqual(update_controls(ControlState(target_throttle=132,throttle=100),supplied).state.throttle,108)
        self.assertEqual(update_controls(ControlState(target_throttle=68,throttle=100),supplied).state.throttle,84)
        self.assertEqual(update_controls(ControlState(target_throttle=99,throttle=100),supplied).state.throttle,99)

    def test_brake_attack_release_and_local_limit(self):
        s=ControlState(target_brake=100,brake=50)
        self.assertEqual(update_controls(s,supplied).state.brake,60)
        self.assertEqual(update_controls(replace(s,target_brake=20),supplied).state.brake,20)
        self.assertEqual(update_controls(replace(s,local_player=True,brake_limit=55),supplied).state.brake,55)

    def test_legacy_sign_reversal_zeroes_once(self):
        s=ControlState(new_steering_mode=False,target_steering=-127,steering=90)
        first=update_controls(s,supplied).state;second=update_controls(first,supplied).state
        self.assertEqual(first.steering,0)
        self.assertEqual(second.steering,-16)

    def test_legacy_magnitude_boundaries(self):
        s=ControlState(new_steering_mode=False,target_steering=127)
        self.assertEqual(update_controls(replace(s,steering=96),supplied).state.steering,100)
        self.assertEqual(update_controls(replace(s,steering=97),supplied).state.steering,99)

    def test_new_mode_slow_return_hold_and_two_unit_attack(self):
        s=ControlState(target_steering=0,steering=30,slow_steering=1)
        self.assertEqual(update_controls(s,supplied).state.steering,30)
        self.assertEqual(update_controls(replace(s,target_steering=-80),supplied).state.steering,28)

    def test_new_direct_copy_differs_from_legacy_ramp(self):
        s=ControlState(smooth_steering=False,target_steering=160,steering=0)
        self.assertEqual(update_controls(s,supplied).state.steering,160)
        self.assertEqual(update_controls(replace(s,new_steering_mode=False),supplied).state.steering,32)

    def test_nearest_even_configuration_conversion(self):
        s=ControlState(target_steering=100,steering_attack_rate=2.5)
        self.assertEqual(update_controls(s,supplied).state.steering,2)
        self.assertEqual(update_controls(replace(s,steering_attack_rate=3.5),supplied).state.steering,4)

    def test_override_query_and_trace_boundary_order(self):
        observed=[]
        def executor(call,s):
            observed.append((call.stage,s.brake_output))
            if call.stage=='override_query':return True
            if call.stage=='trace_controls':s.brake_output=999
            return False
        s=ControlState(emergency=True,target_throttle=100,throttle=200,target_steering=50,steering=30,brake_output=.123)
        out=update_controls(s,executor)
        self.assertEqual([x.stage for x in out.calls],['manual_gears','override_query','trace_controls'])
        self.assertEqual(out.state.steering,0)
        self.assertEqual(out.state.throttle,0)
        self.assertEqual(out.state.brake,192)
        self.assertEqual(observed[-1][1],f32(.123))
        self.assertNotEqual(out.state.brake_output,999)

    def test_throttle_drop_flag_and_external_gate(self):
        s=ControlState(target_throttle=0,throttle_output=.5,flags=0x80)
        out=update_controls(s,supplied).state
        self.assertEqual(out.flags,0x84)
        self.assertEqual(update_controls(out,supplied).state.flags,0x80)
        self.assertEqual(update_controls(s,lambda c,s:False).state.brake,255)

    def test_missing_executor_and_bad_input_rejected(self):
        with self.assertRaises(ValueError):update_controls(ControlState(),None)
        with self.assertRaises(ValueError):update_controls(ControlState(target_throttle=256),supplied)
        with self.assertRaises(ValueError):update_controls(ControlState(),lambda c,s:None)

if __name__=='__main__':unittest.main()
