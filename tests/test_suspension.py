import unittest
from client.physics_data import PhysicsRecord
from client.suspension import Spring, Shock


class SuspensionTests(unittest.TestCase):
    def test_recovered_fields_and_native_limits(self):
        spring=Spring.from_physics(PhysicsRecord(12001,1,5,(12250,0)))
        self.assertEqual((spring.rate,spring.style),(12250,0))
        self.assertAlmostEqual(spring.roll_contribution(1.2),12250*(1.2*0.76)**2*0.0087265)
        self.assertLess(spring.roll_contribution(1.2,front=False),spring.roll_contribution(1.2))
        with self.assertRaisesRegex(ValueError,'axle width'):
            spring.roll_contribution(0)
        shock=Shock.from_physics(PhysicsRecord(11001,1,3,(0.2,0.2032)))
        self.assertEqual((shock.coefficient,shock.length),(0.2,0.2032))
        for cls,record in ((Spring,PhysicsRecord(0,1,5,(9999,0))),
                           (Shock,PhysicsRecord(0,1,3,(0.5,0.2032))),
                           (Shock,PhysicsRecord(0,1,None,(0.2,0.2032)))):
            with self.assertRaises(ValueError):cls.from_physics(record)
