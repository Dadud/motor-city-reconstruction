from dataclasses import replace
import unittest
from client.control_update import ControlState
from client.driving_controls import DrivingControls
from client.driving_pipeline import DrivingForces
from client.vehicle_update import UpdateCall, update_vehicle
from tests.test_driving_pipeline import state, inputs, external


class DrivingControlTests(unittest.TestCase):
    def child(self, call, current):
        if call.stage == 'manual_gears': current.output_gear=3
        if call.stage in ('stopped_query', 'override_query'): return False
        if call.stage == 'vehicle_gate': return True

    def test_smoothed_controls_feed_tire_and_force_inputs_across_ticks(self):
        p=inputs(); control=ControlState(target_throttle=255,target_brake=255,
            target_steering=-127,steering=40,reverse_control=1)
        published=[]
        driver=DrivingControls(control,self.child,external,
            lambda c,s,f: published.append((c.flags,c.throttle_output,f.tire.raw_control)))
        first=update_vehicle(state(),DrivingForces(p,driver,lambda *args:None))
        self.assertEqual(p.tire.raw_control,32)
        self.assertEqual(p.spin.direction_mode,3)
        self.assertTrue(p.parking_control)
        self.assertGreater(p.other_control,0)
        before=p.other_control
        update_vehicle(first.state,DrivingForces(p,driver,lambda *args:None))
        self.assertEqual(p.tire.raw_control,24)
        self.assertGreater(p.other_control,before)
        self.assertEqual(len(published),2)

    def test_remote_flag_and_engine_flag_publication_are_explicit(self):
        p=inputs(); s=state(); s.flags=0x200; seen=[]
        def child(call,current):
            if call.stage=='remote_controls': seen.append(True); current.target_throttle=0
            return self.child(call,current)
        driver=DrivingControls(ControlState(throttle=255,throttle_output=1),child,external,
            lambda c,s,f: seen.append(c.flags))
        driver(UpdateCall('control_update'),s,p)
        self.assertEqual(seen,[True,4])
        self.assertTrue(driver.controls.remote_controls)

    def test_unknown_stages_and_missing_publication_are_not_dropped(self):
        def unknown(call,*args): raise NotImplementedError(call.stage)
        driver=DrivingControls(ControlState(),self.child,unknown,lambda *args:None)
        with self.assertRaisesRegex(NotImplementedError,'engine'):
            driver(UpdateCall('engine'),state(),inputs())
        with self.assertRaises(ValueError):
            DrivingControls(ControlState(),self.child,external,None)


if __name__=='__main__': unittest.main()
