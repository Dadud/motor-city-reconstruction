import tempfile
from pathlib import Path
import unittest
import struct

from client.dyno import FlowTemplate, build_dyno_record, intake_rpm_correction, load_flow_templates
from client.engine import EngineBlock, CylinderHead, Camshaft, ValveTrain


class FlowInputsTests(unittest.TestCase):
    def test_native_builder_geometry_float32_regression(self):
        block = EngineBlock(.07779, .09525, 3.6213, 8, 75)
        head = CylinderHead(0, 0, 0, 1, 6.15, 40.64, 40.64, 30)
        cam = Camshaft(0, 1, 1, 6.64, 6.31, (12, 62, 66, 10), 10)
        train = ValveTrain(0, 1, 18)
        template = FlowTemplate(1, (2, 1.6, 25, 25), ((1,)*8,)*4)
        data = build_dyno_record(block, head, cam, train, template,
            intake_mode=2, intake_flow=1, exhaust_mode=1, exhaust_flow=1,
            carb_capacity=100, carb_code=2)
        self.assertEqual(data[0x8c:0x90].hex(), 'a3014440')
        self.assertEqual(data[0xb8:0xbc].hex(), '82d8853e')

    def test_dyno_record_layout_timing_permutation_and_flow_series(self):
        block = EngineBlock(.1, .09, 5.6, 8, 70)
        head = CylinderHead(2, 0, 1, 1, 20, 40, 30, 30)
        cam = Camshaft(1, 0, 1, 8, 9, (12, 62, 66, 10), 10)
        train = ValveTrain(2, 1, 18)
        template = FlowTemplate(10, (1, 2, 25, 30),
                                tuple((float(i),)*8 for i in range(1, 5)))
        data = build_dyno_record(block, head, cam, train, template,
            intake_mode=2, intake_flow=2, exhaust_mode=3, exhaust_flow=.5,
            carb_capacity=250, carb_code=4)
        self.assertEqual(len(data), 1004)
        self.assertEqual(struct.unpack_from('<h', data, 0x80)[0], 2)
        self.assertEqual(struct.unpack_from('<h', data, 0x84)[0], 3)
        self.assertEqual(struct.unpack_from('<h', data, 0xa4)[0], 300)
        self.assertEqual(struct.unpack_from('<4f', data, 0xa8), (66, 10, 12, 62))
        self.assertEqual(struct.unpack_from('<f', data, 0xa0)[0], 18)
        self.assertAlmostEqual(struct.unpack_from('<f', data, 0x70)[0], 1.1)
        self.assertAlmostEqual(struct.unpack_from('<f', data, 0x7c)[0], .95)
        for offset, value in ((0x324, 3), (0x34c, 4), (0x374, 1), (0x39c, 2)):
            self.assertEqual(struct.unpack_from('<8f', data, offset), (value,)*8)
            self.assertEqual(data[offset+32:offset+40], bytes(8))
        self.assertEqual(data[0xc4:0x2dc], bytes(0x2dc-0xc4))

    def test_intake_inputs_match_native_float32_storage(self):
        # Emulated original 0x479c5e–0x479df6, FPCW 0x27f. Keeping the
        # caller's double 1.08 instead of its stored float32 differs by 1 ULP.
        self.assertEqual(intake_rpm_correction(1, 2000, 1.08), 1.6962043046951294)

    def test_intake_correction_caps_piecewise_and_negative_branch(self):
        self.assertEqual(intake_rpm_correction(1, 11000, 1), 7.5)
        self.assertEqual(intake_rpm_correction(2, 11000, 1), 5)
        self.assertEqual(intake_rpm_correction(4, 11000, 1), 7.5)
        self.assertEqual(intake_rpm_correction(6, 11000, 1), 4.5)
        self.assertEqual(intake_rpm_correction(5, 4000, 1), 4)
        self.assertAlmostEqual(intake_rpm_correction(5, 5000, 1), 3, places=6)
        self.assertAlmostEqual(intake_rpm_correction(5, 11000, 1), -3, places=6)
        self.assertGreater(intake_rpm_correction(3, 11000, 1), 7.5)
        self.assertAlmostEqual(intake_rpm_correction(6, 11000, 1.08), 4.86, places=6)

    def test_intake_correction_rejects_unsupported_solver_inputs(self):
        for args in ((0, 2000, 1), (True, 2000, 1), (1, 0, 1),
                     (1, 11001, 1), (1, 2000, float('nan')), (1, 2000, 2)):
            with self.assertRaises(ValueError):
                intake_rpm_correction(*args)

    def test_scaling_preserves_axes_and_does_not_mutate_source(self):
        source = FlowTemplate(1, [1, 2, 3, 4], [[2]*8, [3]*8, [4]*8, [5]*8])
        scaled = source.scaled(0.5)
        self.assertEqual(scaled.series, ((1,)*8, (3,)*8, (2,)*8, (5,)*8))
        self.assertEqual(source.series[0], (2,)*8)
        self.assertEqual(scaled.scalar_fields, source.scalar_fields)

    def test_non_finite_or_overflow_scale_rejected(self):
        template = FlowTemplate(1, (1,)*4, ((2,)*8,)*4)
        for modifier in (float('nan'), float('inf'), 1e40):
            with self.assertRaises(ValueError):
                template.scaled(modifier)

    def test_unknown_binary_rejected_before_offset_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'unknown.exe'
            path.write_bytes(b'MZ')
            with self.assertRaisesRegex(ValueError, 'unsupported executable'):
                load_flow_templates(path)

    def test_template_shape_rejected(self):
        with self.assertRaises(ValueError):
            FlowTemplate(1, (1,)*4, ((1,)*7,)*4)
