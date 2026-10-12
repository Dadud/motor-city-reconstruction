import unittest
from client.tires import TireDimensions
from client.physics_data import PhysicsRecord


class TireTests(unittest.TestCase):
    def test_verified_database_value_binding(self):
        tire=TireDimensions.from_physics(PhysicsRecord(110001,1,10,(150,82,18,5)))
        self.assertAlmostEqual(tire.radius,0.3516)
        with self.assertRaisesRegex(ValueError,'requires'):
            TireDimensions.from_physics(PhysicsRecord(110001,1,10,(150,82)))

    def test_metric_radius_and_separate_large_tire_stance(self):
        tire=TireDimensions(225,60,15)
        self.assertAlmostEqual(tire.sidewall,0.135)
        self.assertAlmostEqual(tire.radius,0.3255)
        self.assertEqual(tire.stance_adjustment,0)
        tire=TireDimensions(350,80,20)
        self.assertAlmostEqual(tire.radius,0.534)
        self.assertAlmostEqual(tire.stance_adjustment,0.164)

    def test_invalid_dimensions(self):
        for values in ((0,60,15),(225,-1,15),(float('nan'),60,15),(225,60,101)):
            with self.assertRaises(ValueError):
                TireDimensions(*values)
