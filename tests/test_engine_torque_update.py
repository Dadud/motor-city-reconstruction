import unittest
from dataclasses import replace
from client.engine_torque_update import *
from tools.engine_torque_update_oracle import base,SuppliedTorqueStages

class EngineTorqueUpdateTests(unittest.TestCase):
    def setUp(self):self.s,self.c=base()
    def run_update(self,s=None,c=None,**observations):
        return update_engine_torque(s or self.s,c or self.c,SuppliedTorqueStages({'rpm_limit':10000,**observations}))
    def test_disabled_retains_stored_curve_and_initial_normalization(self):
        s=replace(self.s,engine_flags=0,drag_factor=0)
        out=self.run_update(s)
        self.assertEqual(out.state.rpm_state.rpm,0)
        self.assertEqual(out.state.engagement,0)
        self.assertEqual(out.state.effective_torque,0)
        self.assertEqual(out.state.curve_torque,s.curve_torque)
        self.assertEqual(out.state.rpm_state.normalized_rpm,f32(s.rpm_state.rpm/s.rpm_state.limiter_rpm))
    def test_below_idle_halves_engagement_and_leaves_curve_field(self):
        s=replace(self.s,rpm_state=replace(self.s.rpm_state,rpm=599))
        out=self.run_update(s)
        self.assertGreaterEqual(out.state.rpm_state.rpm,600)
        self.assertEqual(out.state.engagement,f32(.25))
        self.assertEqual(out.state.curve_torque,100)
        self.assertEqual(out.state.power,f32(600*100*f32(.00010471976)))
    def test_coasting_uses_low_query_byte_and_clears_flag(self):
        s=replace(self.s,rpm_state=replace(self.s.rpm_state,throttle=0),engine_flags=9,brake_control=.5,drag_factor=0)
        a=self.run_update(s,brake_query=0);b=self.run_update(s,brake_query=1);d=self.run_update(s,brake_query=256)
        self.assertAlmostEqual(a.state.effective_torque*.5,b.state.effective_torque,places=5)
        self.assertEqual(a.state.effective_torque,d.state.effective_torque)
        self.assertEqual(a.state.engine_flags,1)
    def test_gain_boundaries_use_initial_throttle(self):
        c=replace(self.c,gain_mode=3)
        low=self.run_update(replace(self.s,rpm_state=replace(self.s.rpm_state,throttle=.8)),c)
        high=self.run_update(replace(self.s,rpm_state=replace(self.s.rpm_state,throttle=.800001)),c)
        curve=f32(curve_torque_at_rpm(c.torque_curve,self.s.rpm_state.rpm))
        self.assertEqual(low.state.curve_torque,f32(curve*f32(1.03)))
        self.assertEqual(high.state.curve_torque,f32(curve*f32(1.0609)))
    def test_boost_is_explicit_and_adds_both_outputs(self):
        s=replace(self.s,alternate_enabled=True)
        a=self.run_update(s,boost=(0.,0.));b=self.run_update(s,boost=(17.5,.25))
        self.assertEqual(b.state.boost_flag,1)
        self.assertEqual(b.state.boost_observation,.25)
        self.assertEqual(b.state.curve_torque,f32(a.state.curve_torque+17.5))
        self.assertEqual([c.stage for c in b.calls[:3]],['boost','environment','rpm_update'])
    def test_condition_effect_priority_and_clamp(self):
        s=replace(self.s,damage_d40=.5,damage_d4c=1.)
        a=self.run_update(s,pulse=1.5);b=self.run_update(s,pulse=.8)
        self.assertEqual(a.calls[0].stage,'pulse')
        self.assertEqual(a.calls[0].values[1:],(f32(.5),f32(.02),f32(.25)))
        self.assertEqual(a.state.effective_torque,b.state.effective_torque)
    def test_post_rpm_damage_order(self):
        s=replace(self.s,rpm_state=replace(self.s.rpm_state,rpm=8000,throttle=.9,angular_speed=f32(8000*f32(.10471976))))
        c=replace(self.c,durability_index=1,overspeed_base=1000,overload_index=1,torque_capacity=50)
        out=self.run_update(s,c,rpm_limit=2500)
        damage=[c.code for c in out.calls if c.stage=='damage']
        self.assertEqual(damage,[7,9,14,8,12])
        self.assertEqual(out.calls[1].stage,'rpm_update')
    def test_invalid_inputs_and_copy(self):
        before=self.s.rpm_state
        self.run_update();self.assertEqual(self.s.rpm_state,before)
        with self.assertRaises(ValueError):update_engine_torque(self.s,self.c,None)
        with self.assertRaises(ValueError):self.run_update(c=replace(self.c,torque_capacity=0))
        with self.assertRaises(ValueError):self.run_update(replace(self.s,rpm_state=replace(self.s.rpm_state,throttle=2.)))

if __name__=='__main__':unittest.main()
