import unittest
from dataclasses import replace
from client.rolling_resistance import ResistanceWheel, rolling_resistance


class RollingResistanceTests(unittest.TestCase):
    def setUp(self):
        self.wheels = (ResistanceWheel(0.01, 2, 1000, 2, 2, True, 100),) * 4

    def run_model(self, wheels=None, speed=20, **options):
        return rolling_resistance(self.wheels if wheels is None else wheels,
                                  speed, 1, 1, 0, 0, 0, **options)

    def test_mode_and_speed_gates_preserve_forces(self):
        for speed, options in ((1.999, {}), (-1.999, {}), (20, {'disabled_flag': True}),
                               (20, {'mode_predicate': True})):
            result = self.run_model(speed=speed, **options)
            self.assertEqual(tuple(w.longitudinal_force for w in result.wheels), (100,) * 4)
            self.assertEqual(result.last_contribution, 0)
        self.assertLess(self.run_model(speed=2).last_contribution, 0)

    def test_direction_contact_and_strict_speed_threshold(self):
        wheels = (self.wheels[0], replace(self.wheels[1], rolling_speed=-2),
                  replace(self.wheels[2], contact=False),
                  replace(self.wheels[3], rolling_speed=0.5))
        result = self.run_model(wheels)
        self.assertLess(result.wheels[0].longitudinal_force, 100)
        self.assertGreater(result.wheels[1].longitudinal_force, 100)
        self.assertEqual(result.wheels[2].longitudinal_force, 100)
        self.assertEqual(result.wheels[3].longitudinal_force, 100)
        self.assertLess(result.last_contribution, 0)  # Computed even if not applied.

    def test_surface_and_alternate_slip_amplification(self):
        wheels = tuple(replace(wheel, surface_id=surface, slip_angle=0.2)
                       for wheel, surface in zip(self.wheels, (2, 3, 5, 0)))
        baseline, alternate = self.run_model(wheels), self.run_model(wheels, alternate=True)
        self.assertEqual(baseline.wheels[1].longitudinal_force, baseline.wheels[2].longitudinal_force)
        self.assertLess(alternate.last_contribution, baseline.last_contribution)
        self.assertAlmostEqual(alternate.last_contribution, baseline.last_contribution * 8, places=4)

    def test_invalid_wheel_observations(self):
        for change in ({'normal_load': -1}, {'speed_scale': 0}, {'surface_id': -1},
                       {'slip_angle': float('nan')}):
            wheels = (replace(self.wheels[0], **change),) + self.wheels[1:]
            with self.assertRaises(ValueError):
                self.run_model(wheels)
        with self.assertRaises(ValueError):
            self.run_model(self.wheels[:3])

    def test_original_combined_product_store_order(self):
        wheels=tuple(ResistanceWheel((i-1)*.01,surface,0 if i==3 else 1500+i*500,
            -2,2,True,100+i) for i,surface in enumerate((2,3,5,0)))
        result=rolling_resistance(wheels,20,1.2,.8,.3,-.1,.1)
        self.assertEqual(tuple(w.longitudinal_force for w in result.wheels),
            (113.17597198486328,119.2242431640625,112.51398468017578,103.0))


if __name__ == '__main__':
    unittest.main()
