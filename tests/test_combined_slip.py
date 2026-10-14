from dataclasses import replace
import math
import unittest
from client.combined_slip import CombinedSlipState,CombinedSlipWheel,longitudinal_slip_factor,limit_combined_slip


class CombinedSlipTests(unittest.TestCase):
    def state(self):
        w=CombinedSlipWheel(0,0,0,10,100,1,.5,1,.3,20,True,6,1)
        return CombinedSlipState((w,)*4,20,False,False,0,0,0)

    def test_curve_discontinuity_and_tail_floors(self):
        self.assertEqual(longitudinal_slip_factor(-.05),1)
        self.assertLess(longitudinal_slip_factor(-.05000001),.25)
        self.assertEqual(longitudinal_slip_factor(.15),1)
        self.assertEqual(longitudinal_slip_factor(-100),.125)
        self.assertEqual(longitudinal_slip_factor(100),.0625)

    def test_reverse_and_exact_speed_gate_skip_curve(self):
        s=self.state();wheels=tuple(replace(w,slip_ratio=2,longitudinal_force=40) for w in s.wheels)
        for speed in (-20,1):
            out,_=limit_combined_slip(replace(s,wheels=wheels,speed=speed))
            self.assertEqual(out.wheels[0].longitudinal_force,40)
        out,_=limit_combined_slip(replace(s,wheels=wheels,speed=1.0001))
        self.assertLess(out.wheels[0].longitudinal_force,40)

    def test_parking_disables_rear_transfer(self):
        s=self.state();wheels=list(s.wheels)
        wheels[2]=replace(wheels[2],longitudinal_force=50)
        wheels[3]=replace(wheels[3],longitudinal_force=200)
        out,_=limit_combined_slip(replace(s,wheels=tuple(wheels)))
        parked,_=limit_combined_slip(replace(s,wheels=tuple(wheels),parking_control=True))
        self.assertEqual(out.wheels[2].longitudinal_force,100)
        self.assertEqual(parked.wheels[2].longitudinal_force,50)

    def test_combined_force_and_secondary_response_are_scaled(self):
        s=self.state();wheels=tuple(replace(w,lateral_force=200,longitudinal_force=200) for w in s.wheels)
        out,_=limit_combined_slip(replace(s,wheels=wheels,parking_control=True))
        self.assertLess(out.wheels[0].lateral_force,200)
        self.assertLess(out.wheels[0].longitudinal_force,200)
        self.assertLess(out.wheels[0].secondary_response,10)

    def test_effects_are_gated_by_contact_and_ordered(self):
        s=self.state();wheels=tuple(replace(w,slip_ratio=2,longitudinal_force=200,component_code=0) for w in s.wheels)
        _,effects=limit_combined_slip(replace(s,wheels=wheels))
        self.assertTrue(effects)
        self.assertEqual(effects[0].operation,0)
        self.assertTrue(any(e.operation==1 for e in effects))
        _,airborne=limit_combined_slip(replace(s,wheels=tuple(replace(w,contact=False) for w in wheels)))
        self.assertEqual(airborne,())

    def test_invalid_inputs(self):
        s=self.state()
        for invalid in (replace(s,wheels=s.wheels[:3]),replace(s,speed=math.nan)):
            with self.assertRaises(ValueError):limit_combined_slip(invalid)
