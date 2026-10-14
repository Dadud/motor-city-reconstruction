import unittest
from types import SimpleNamespace

from client.contact import WheelRig
from client.physics_data import PhysicsRecord
from client.simulation_inputs import build_stock_simulation_inputs
from client.suspension import Shock, Spring
from client.tires import TireDimensions


class SimulationInputTests(unittest.TestCase):
    def test_collects_recovered_wheel_and_engine_inputs(self):
        vehicle = SimpleNamespace(branded_id=9, parts=(
            SimpleNamespace(abstract_type_id=110001, part_type_id=1, attachment_id=1),
            SimpleNamespace(abstract_type_id=110001, part_type_id=1, attachment_id=2),
            SimpleNamespace(abstract_type_id=110001, part_type_id=1, attachment_id=3),
            SimpleNamespace(abstract_type_id=110001, part_type_id=1, attachment_id=4),
            SimpleNamespace(abstract_type_id=12001, part_type_id=2, attachment_id=10),
            SimpleNamespace(abstract_type_id=11001, part_type_id=3, attachment_id=10),
            SimpleNamespace(abstract_type_id=160001, part_type_id=4, attachment_id=0),
        ))
        catalogue = SimpleNamespace(
            tire_dimensions=lambda v: {k: TireDimensions(205, 60, 15) for k in ('LF', 'RF', 'LR', 'RR')},
            suspension=lambda v: {k: (Spring.from_physics(PhysicsRecord(12001, 1, 5, (12250, 0))),
                                      Shock.from_physics(PhysicsRecord(11001, 1, 3, (0.2, 0.2032))))
                                  for k in ('LF', 'RF', 'LR', 'RR')},
            engine_block=lambda v: SimpleNamespace(mass=120.0, bore_m=0.1),
        )
        rig = WheelRig(((-0.7, 0, 1.3), (0.7, 0, 1.3), (-0.7, 0, -1.3), (0.7, 0, -1.3)))
        inputs = build_stock_simulation_inputs(catalogue, vehicle, rig)
        self.assertEqual(inputs.vehicle_id, 9)
        self.assertAlmostEqual(inputs.wheelbase_m, 2.6)
        self.assertEqual(inputs.engine_mass_kg, 120.0)
        self.assertEqual(len(inputs.tire_radii_m), 4)
        self.assertAlmostEqual(inputs.simulation_step_s, 1 / 32)


if __name__ == '__main__':
    unittest.main()

