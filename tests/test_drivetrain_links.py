import unittest
from dataclasses import replace
from client.drivetrain_links import *

class DrivetrainLinksTests(unittest.TestCase):
    def setUp(self):self.s=DrivetrainLinksState();self.c=DrivetrainLinksConfig();self.empty=lambda action,state:None
    def test_gate_saturation_and_request_order(self):
        out=update_gear_link(replace(self.s,gate_one=.8,request=.1,auxiliary_temperature=201),self.c,self.empty)
        self.assertEqual(out.state.engagement,0)
        self.assertEqual([(c.stage,c.code) for c in out.calls],[('damage',4),('effect_range',23),('damage',5)])
        self.assertEqual(self.s.gate_one,.1)
    def test_disabled_clears_engagement_without_gate_damage(self):
        out=update_gear_link(replace(self.s,engine_flags=0,gate_one=1),self.c,self.empty)
        self.assertEqual(out.state.engagement,0);self.assertEqual(out.calls,())
    def test_bypass(self):
        out=update_drivetrain_loads(replace(self.s,bypass=True,condition=1.1),self.c,self.empty)
        self.assertEqual((out.state.main_temperature,out.state.auxiliary_temperature,out.state.condition),(100.,125.,f32(.9)))
        self.assertEqual(out.calls,())
    def test_saturated_cooling_emits_three_ordered_calls(self):
        out=update_drivetrain_loads(replace(self.s,gate_two=1.,engagement=0),self.c,self.empty)
        self.assertEqual(out.state.condition,1);self.assertEqual(out.state.auxiliary_temperature,150)
        self.assertEqual([c.code for c in out.calls],[3,18,22])
    def test_damage_mutation_is_consumed_by_next_effect(self):
        def execute(action,state):
            if action.stage=='damage' and action.code==15:state.third_temperature=150
        out=update_drivetrain_loads(replace(self.s,third_temperature=200),self.c,execute)
        self.assertEqual(out.state.third_temperature,150)
        self.assertEqual(out.calls[1].values,(f32(150*f32(.00024038462)),))
    def test_boundary_and_invalid_inputs(self):
        self.assertEqual(update_drivetrain_loads(replace(self.s,main_temperature=89.999),self.c,self.empty).state.loss,0)
        self.assertGreater(update_drivetrain_loads(replace(self.s,main_temperature=90),self.c,self.empty).state.loss,0)
        for s,c in ((self.s,replace(self.c,reference=0)),(replace(self.s,engagement=.5,gate_one=1),self.c),(replace(self.s,mode=255),self.c)):
            with self.assertRaises(ValueError):update_drivetrain_loads(s,c,self.empty)
        with self.assertRaises(ValueError):update_gear_link(self.s,self.c,None)
        with self.assertRaises(ValueError):update_gear_link(self.s,replace(self.c,material_index=-4),self.empty)

if __name__=='__main__':unittest.main()
