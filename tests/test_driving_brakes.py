from dataclasses import replace
import struct
import unittest
from client.driving_brakes import DrivingBrakes
from client.vehicle_update import UpdateCall
from tests import test_driving_engine as engine_fixture
from tools.brake_forces_oracle import cases


class DrivingBrakeTests(unittest.TestCase):
    def fixture(self):
        engine,s,f=engine_fixture.DrivingEngineTests().fixture()
        b=next(b for b in cases() if b.thermal.front.material_code==2 and b.thermal.front.temperature==900)
        b=replace(b,thermal=replace(b.thermal,front=replace(b.thermal.front,temperature=200),
            rear=replace(b.thermal.rear,temperature=175)))
        s.speed=20.;f.service_control=1.;f.parking_control=False
        for w in s.wheels:w.force=(12.,4000.,0.);w.projected_speed=20.;w.spin=40.
        captured=[]
        d=DrivingBrakes(b,(.2,.4,.8,1.2),engine.controls,engine.loads,engine.environment,
            lambda events,*args:captured.extend(events),engine)
        return d,s,f,captured

    def test_brake_outputs_feed_longitudinal_force_and_spin_adjustment(self):
        d,s,f,_=self.fixture();d(UpdateCall('brakes'),s,f)
        self.assertLess(s.wheels[0].force[2],0)
        self.assertLess(f.spin.wheels[0].spin_adjustment,0)
        self.assertEqual(s.wheels[0].force[:2],(12.,4000.))
        self.assertEqual(d.last_input.wheels[0].inertia_addend,f.spin.wheels[0].kinetic_parameter)
        self.assertEqual(d.last_input.wheels[0].control_angle,f.spin.wheels[0].slip_ratio)

    def test_selected_gear_factor_changes_inertia_without_inventing_ratios(self):
        d,s,f,_=self.fixture();f.spin=replace(f.spin,direction_mode=3)
        d(UpdateCall('brakes'),s,f)
        self.assertEqual(d.last_input.drive_factor,1.2)
        d2,s2,f2,_=self.fixture();f2.spin=replace(f2.spin,direction_mode=2)
        d2(UpdateCall('brakes'),s2,f2)
        self.assertEqual(d2.last_input.drive_factor,.8)
        self.assertNotEqual(f.spin.wheels[0].spin_adjustment,f2.spin.wheels[0].spin_adjustment)

    def test_retains_previous_braking_work_and_uses_current_environment(self):
        d,s,f,_=self.fixture();d(UpdateCall('brakes'),s,f)
        previous=d.state.thermal.wheels[0].brake_force
        temperature=d.state.thermal.front.temperature
        d.environment.environment=replace(d.environment.environment,weather_enabled=False,weather_code=2,altitude=1000.)
        d(UpdateCall('brakes'),s,f)
        self.assertEqual(d.last_input.thermal.wheels[0].brake_force,previous)
        self.assertEqual(d.last_input.thermal.front.temperature,temperature)
        self.assertEqual(d.last_input.thermal.environment_code,0)
        self.assertEqual(d.state.thermal.elevation_parameter,1000.)
        self.assertEqual(d.state.thermal.mass_parameter,1300.)

    def test_engine_auxiliary_flag_applies_rear_parking_behavior(self):
        d,s,f,_=self.fixture();f.service_control=0.
        d.controls.controls.flags=0x20;d(UpdateCall('brakes'),s,f)
        self.assertEqual(d.state.parking_ramp,8)
        self.assertEqual(s.wheels[0].force[2],0.)
        self.assertLess(s.wheels[2].force[2],0.)

    def test_wear_and_controller_events_retain_interleaving(self):
        d,s,f,captured=self.fixture()
        d.state=replace(d.state,thermal=replace(d.state.thermal,front=replace(d.state.thermal.front,temperature=900)))
        d(UpdateCall('brakes'),s,f)
        self.assertEqual([(e.kind,e.slot) for e in captured[:4]],
            [('wear',0),('controller',0),('wear',1),('controller',1)])
        self.assertEqual(tuple(captured),d.events)

    def test_missing_factor_or_effect_consumer_is_rejected(self):
        d,s,f,_=self.fixture();f.spin=replace(f.spin,direction_mode=8)
        with self.assertRaisesRegex(ValueError,'selected gear'):d(UpdateCall('brakes'),s,f)
        with self.assertRaises(ValueError):DrivingBrakes(d.state,(),d.controls,d.loads,d.environment,None,d.external)

    def test_conditioned_observation_requires_exact_formulas_for_both_inputs(self):
        from tools.driving_brakes_pipeline_oracle import BrakeExtension
        extension=BrakeExtension();_,_,f,_=self.fixture()
        f.spin=replace(f.spin,wheels=(replace(f.spin.wheels[0],spin_value=10.566805839538574,
            projected_speed=2.4678502082824707,spin_scale=.2800000011920929),*f.spin.wheels[1:]))
        extension.force_inputs=f;extension.combined_before=bytearray(0x2000)
        for off,value in ((0x7c,10.56680679321289),(0x10,2.4678502082824707),(0xbc,.2800000011920929)):
            struct.pack_into('<f',extension.combined_before,0x5fc+off,value)
        a,b=.05478300154209137,.05478297173976898
        self.assertTrue(extension.conditioned_secondary(0,a,b))
        self.assertFalse(extension.conditioned_secondary(0,a+.000001,b))
        self.assertFalse(extension.conditioned_secondary(0,a,b+.000001))


if __name__=='__main__':unittest.main()
