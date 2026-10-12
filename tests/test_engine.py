import math
import unittest

from client.engine import Camshaft, CylinderHead, EngineBlock, TorqueCurve, ValveTrain
from client.physics_data import PhysicsRecord


class EngineTests(unittest.TestCase):
    def test_cam_timing_and_valve_train_effective_lift(self):
        cam = Camshaft.from_physics(PhysicsRecord(1, 1, 10,
            (0, 1, 1, 6.64, 6.31, 12, 62, 66, 10)))
        train = ValveTrain.from_physics(PhysicsRecord(2, 1, 10, (0, .95)))
        self.assertEqual(cam.timing_fields, (12, 62, 66, 10))
        lift = cam.valve_lift_inches(train.lift_factor)
        self.assertAlmostEqual(lift[0], .24834658922)
        self.assertAlmostEqual(lift[1], .23600406395)
        for factor in (0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                cam.valve_lift_inches(factor)

    def test_cam_and_train_invalid_physics_rejected(self):
        for record in (PhysicsRecord(1, 1, 10, (0,)*8),
                       PhysicsRecord(1, 1, 10, (0, 1, 1, 4, 6, 0, 0, 0, 0))):
            with self.assertRaises(ValueError):
                Camshaft.from_physics(record)
        for record in (PhysicsRecord(1, 1, 10, (0,)),
                       PhysicsRecord(1, 1, 10, (0, 1.2))):
            with self.assertRaises(ValueError):
                ValveTrain.from_physics(record)

    def test_head_compression_is_separate_from_block_displacement(self):
        head = CylinderHead.from_physics(PhysicsRecord(1, 1, 30,
            (0, 0, 0, 1, 6.15, 40.64, 40.64)))
        self.assertEqual(head.compression_ratio, 6.15)
        self.assertEqual(head.intake_valve_mm, 40.64)
        self.assertEqual(head.flow_template_id(.07779, 1), 3)
        self.assertEqual(head.flow_template_id(.07779, 10), 1)
        with self.assertRaises(ValueError):
            head.flow_template_id(0, 1)
        with self.assertRaises(ValueError):
            head.flow_template_id(.07779, True)

    def test_head_template_selection_all_port_and_head_branches(self):
        # Independent branch expectations from the native switch in REA 198.
        small = ((1, 2, 7, 8, 7, 8), (4, 5, 7, 8, 7, 8), (9, 10, 12, 13, 12, 13))
        large = ((3, 2, 7, 8, 7, 8), (4, 6, 7, 8, 7, 8), (9, 11, 12, 13, 12, 13))
        for kind in range(3):
            for port in range(6):
                head = CylinderHead.from_physics(PhysicsRecord(1, 1, 30,
                    (kind, 0, port, 1, 9, 50, 45)))
                self.assertEqual(head.flow_template_id(.12, 1), small[kind][port])
                self.assertEqual(head.flow_template_id(.08, 1), large[kind][port])
                self.assertEqual(head.flow_template_id(.08, 10), small[kind][port])

    def test_head_incomplete_or_invalid_physics_rejected(self):
        for values in ((0,)*6, (0, 0, 0, 1, 5, 40, 40),
                       (0, 0, 0, math.nan, 9, 40, 40)):
            with self.assertRaises(ValueError):
                CylinderHead.from_physics(PhysicsRecord(1, 1, 30, values))

    def test_block_preserves_database_displacement_discrepancy(self):
        block = EngineBlock.from_physics(PhysicsRecord(1, 1, 70, (0.104775, 0.104775, 6.5699, 8)))
        self.assertEqual(block.displacement_l, 6.5699)
        self.assertAlmostEqual(block.geometric_displacement_l, 7.226913837)
        self.assertEqual(block.cylinders, 8)
        for record in (PhysicsRecord(1, 1, None, ()),
                       PhysicsRecord(1, 1, 70, (math.nan, .1, 5, 8)),
                       PhysicsRecord(1, 1, 70, (.1, .1, 5, 4))):
            with self.assertRaises(ValueError):
                EngineBlock.from_physics(record)

    def test_curve_knots_interpolation_power_and_cutoff(self):
        # Synthetic assembled curve; no claim these are stock engine outputs.
        curve = TorqueCurve((0, 0, 50, 100, 180, 200, 220, 240, 260, 250, 230,
                             200, 150, 80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(curve.torque(4000), 260)
        self.assertEqual(curve.torque(4250), 255)
        self.assertEqual(curve.torque(7000), 0)
        self.assertEqual(curve.torque(11999), 0)
        self.assertAlmostEqual(curve.power_kw(4250), 255*4250*2*math.pi/60000, places=4)
        for rpm in (-1, 12000, 4500.0, True):
            with self.assertRaises(ValueError):
                curve.torque(rpm)
        for samples in ((0,)*24, (math.inf,)*25):
            with self.assertRaises(ValueError):
                TorqueCurve(samples)
