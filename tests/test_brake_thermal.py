import unittest
from dataclasses import replace

from client.brake_thermal import brake_countdown,brake_fade,brake_ambient,update_brake_thermal
from tools.brake_thermal_oracle import cases


class BrakeThermalTests(unittest.TestCase):
    def test_countdown_material_and_construction(self):
        self.assertEqual(brake_countdown(.25,2,1),26)
        self.assertEqual(brake_countdown(.25,3,0),42)

    def test_fade_boundaries(self):
        self.assertEqual(brake_fade(199,200),1)
        self.assertEqual(brake_fade(200,200),1)
        self.assertEqual(brake_fade(225,200),.75)
        self.assertEqual(brake_fade(250,200),.5)
        self.assertEqual(brake_fade(251,200),.5)

    def test_environment_observations(self):
        self.assertEqual(brake_ambient(False,0),15)
        self.assertEqual(brake_ambient(True,2),-15)

    def test_stage_clears_force_but_retains_spin(self):
        s=next(cases());r=update_brake_thermal(s)
        self.assertTrue(all(w.brake_force==0 for w in r.wheels))
        self.assertEqual([w.spin_value for w in r.wheels],[w.spin_value for w in s.wheels])

    def test_temperature_cap_and_countdown_floor(self):
        s=next(cases());s=replace(s,service_control=1,front=replace(s.front,temperature=900,countdown=0))
        r=update_brake_thermal(s)
        self.assertEqual(r.front.temperature,800)
        self.assertEqual(r.front.countdown,0)

    def test_invalid_thermal_denominator(self):
        s=next(cases());s=replace(s,front=replace(s.front,thermal_mass=0))
        with self.assertRaises(ValueError):update_brake_thermal(s)


if __name__=='__main__':unittest.main()
