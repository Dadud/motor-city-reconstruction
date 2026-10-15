import unittest
from dataclasses import replace
from client.engine_pipeline import *
from tools.engine_pipeline_oracle import base,SuppliedPipelineStages

class EnginePipelineTests(unittest.TestCase):
    def setUp(self):self.s,self.c=base()
    def run_update(self,s=None,c=None,**o):
        return update_engine_pipeline(s or self.s,c or self.c,SuppliedPipelineStages({'rpm_limit':10000,**o}))
    def test_two_engagement_records_remain_distinct(self):
        out=self.run_update(replace(self.s,vehicle_flags=7,engagement=.125,thermal_engagement=.9))
        self.assertEqual(out.state.engagement,.125)
        self.assertNotEqual(out.state.thermal_engagement,.125)
        self.assertGreater(out.state.thermal_engagement,.5)
    def test_actual_nested_consumers_keep_dispatch_order(self):
        out=self.run_update()
        self.assertEqual([a.stage for a in out.calls if a.domain=='dispatch'],[
            'engine_setup','engine_control','gear_link','drivetrain_loads','engagement_inputs','torque_update','wheel_drive','engine_finalize'])
        self.assertEqual([a.stage for a in out.calls if a.domain=='torque_update'],['environment','rpm_update','rpm_limit'])
        self.assertNotEqual(out.state.main_temperature,self.s.main_temperature)
        self.assertNotEqual(out.state.rpm_state.rpm,self.s.rpm_state.rpm)
    def test_callback_changes_dispatch_branch_after_torque(self):
        s=replace(self.s,vehicle_flags=6)
        out=self.run_update(s,mutations={('torque_update','rpm_limit'):(('vehicle_flags',7),)})
        self.assertEqual(out.state.vehicle_flags,7)
        self.assertEqual([a.stage for a in out.calls if a.domain=='dispatch'],['torque_update','curve_lookup','gear_link','drivetrain_loads'])
    def test_nested_callback_preserves_fields_outside_child_projection(self):
        s=replace(self.s,vehicle_flags=6,alternate_enabled=True)
        out=self.run_update(s,boost=(17.5,.25),mutations={('torque_update','boost'):(('gate_two',.5),)})
        self.assertEqual(out.state.gate_two,.5)
        self.assertEqual(out.state.boost_observation,.25)
    def test_thermal_damage_can_change_driveline_engagement(self):
        s=replace(self.s,vehicle_flags=7,gate_one=.9)
        out=self.run_update(s,mutations={('gear_link','damage'):(('engagement',.25),)})
        self.assertEqual(out.state.engagement,.25)
        self.assertEqual(out.state.thermal_engagement,0)
    def test_repeated_ticks_preserve_heat_and_state_copy(self):
        a=self.run_update();b=self.run_update(a.state)
        self.assertEqual(self.s.rpm_state.rpm,3000)
        self.assertEqual(self.s.main_temperature,100)
        self.assertNotEqual(a.state.main_temperature,b.state.main_temperature)
        self.assertNotEqual(a.state.rpm_state.rpm,b.state.rpm_state.rpm)
    def test_shared_catalogue_conflicts_are_rejected(self):
        c=replace(self.c,links=replace(self.c.links,material_index=99))
        with self.assertRaisesRegex(ValueError,'shared catalogue'):self.run_update(c=c)
    def test_external_producers_are_required(self):
        with self.assertRaises(ValueError):update_engine_pipeline(self.s,self.c,None)
        def missing(action,state):raise NotImplementedError(action.stage)
        with self.assertRaisesRegex(NotImplementedError,'engine_setup'):update_engine_pipeline(self.s,self.c,missing)

if __name__=='__main__':unittest.main()
