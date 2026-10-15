from dataclasses import replace
import unittest
from client.control_update import ControlState
from client.driving_controls import DrivingControls
from client.driving_engine import DrivingEngine
from client.vehicle_update import UpdateCall
from tools.engine_pipeline_oracle import base, SuppliedPipelineStages
from tests.test_driving_loads import fixture
from tests.test_driving_environment import environment_inputs


class DrivingEngineTests(unittest.TestCase):
    def fixture(self, execute=None):
        s,f,loads=fixture();s.flags=4
        e,c=base();c=replace(c,links=replace(c.links,mode_coefficients=(.8,1.,.7,.9)))
        controls=DrivingControls(ControlState(flags=1),self.control,lambda *a:None,lambda *a:None,lambda s,f:0)
        env=environment_inputs()
        supplied=SuppliedPipelineStages({'rpm_limit':7000})
        driver=DrivingEngine(e,c,controls,loads,env,execute or (lambda a,e,s,f:supplied(a,e)),lambda *a:None)
        return driver,s,f

    @staticmethod
    def control(call,c):
        if call.stage=='manual_gears':c.output_gear=3
        if call.stage=='vehicle_gate':return True
        if call.stage in ('stopped_query','override_query'):return False

    def test_reads_latest_shared_owner_and_weather_before_engine(self):
        seen=[]
        def child(a,e,s,f):
            if a.stage=='engine_setup':
                seen.append((e.rpm_state.throttle,e.brake_control,e.rpm_state.longitudinal_speed,
                    e.rpm_state.rpm,e.effect_motion,e.curve_torque,e.thermal_mode,
                    e.environment_field,e.environment_selector,e.counter))
            return 7000 if a.stage=='rpm_limit' else 0
        d,s,f=self.fixture(child)
        f.other_control=.75;f.service_control=.25;f.spin=replace(f.spin,rpm=1234,direction_mode=3)
        s.local_linear=(1.,2.,17.);s.speed=19.;d.loads.torque=321.
        d(UpdateCall('engine'),s,f)
        self.assertEqual(seen,[(.75,.25,17.,1234,19.,321.,3,500.,2,5)])
        self.assertEqual(d.state.rpm_state.gear_index,2)

    def test_callback_writes_reach_force_load_and_next_control_consumers(self):
        def child(a,e,s,f):
            if a.stage=='engine_finalize':
                e.engine_flags=0x41;e.curve_torque=234.5;e.thermal_mode=3
                e.rpm_state=replace(e.rpm_state,rpm=4321,throttle=.25,longitudinal_speed=11.)
                e.brake_control=.5;e.effect_motion=12.
            return 7000 if a.stage=='rpm_limit' else 0
        d,s,f=self.fixture(child);d(UpdateCall('engine'),s,f)
        self.assertEqual((f.spin.rpm,f.spin.direction_mode),(4321,3))
        self.assertEqual((f.other_control,f.service_control),(.25,.5))
        self.assertEqual((d.loads.torque,s.speed,s.local_linear[2]),(234.5,12.,11.))
        self.assertEqual(d.controls.controls.flags,0x41)
        d.controls(UpdateCall('control_update'),s,f)
        self.assertEqual(d.controls.controls.flags,0x45)

    def test_callbacks_observe_changes_from_previous_recovered_child(self):
        seen=[]
        def child(a,e,s,f):
            if a.stage=='engine_setup':e.rpm_state=replace(e.rpm_state,throttle=.875)
            if a.stage=='engine_control':seen.append((f.other_control,e.rpm_state.throttle))
            return 7000 if a.stage=='rpm_limit' else 0
        d,s,f=self.fixture(child);d(UpdateCall('engine'),s,f)
        self.assertEqual(seen,[(.875,.875)])

    def test_unrecovered_engine_children_are_required(self):
        def missing(a,*args):raise NotImplementedError(a.stage)
        d,s,f=self.fixture(missing)
        with self.assertRaisesRegex(NotImplementedError,'engine_setup'):d(UpdateCall('engine'),s,f)

    def test_conflicting_shared_catalogue_flag_is_rejected(self):
        d,_,_=self.fixture();d.controls.controls.assisted_gears=True
        with self.assertRaisesRegex(ValueError,'0x68c'):
            DrivingEngine(d.state,d.config,d.controls,d.loads,d.environment,d.execute,d.external)


if __name__=='__main__':unittest.main()
