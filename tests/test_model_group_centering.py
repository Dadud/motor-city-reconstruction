import struct
import unittest

from client.model_group_centering import (PreparedModelGroup, SelectedPart,
                                           prepare_model_group)
from client.model_group_centering import (TireModelComponent,
                                           prepare_tire_models,
                                           prepare_rear_suspension_model)
from client.model_group_centering import prepare_vehicle_model_group


def image(origin=(10., 20., 30.), vertices=((0., 0., 0.), (2., 4., 6.)),
          dummies=((1., 2., 3.),)):
    parts, dummy_count = 1, len(dummies)
    out = bytearray(0x2038 + len(vertices)*12)
    struct.pack_into('<4I', out, 0, 0x101015, 0, 0, len(vertices))
    struct.pack_into('<3I', out, 0x14, 0, len(vertices)*12, len(vertices)*24)
    struct.pack_into('<I', out, 0x58, dummy_count)
    struct.pack_into('<I', out, 0x11c, parts)
    struct.pack_into('<3f', out, 0x120, *origin)
    struct.pack_into('<I', out, 0x520, len(vertices))
    for i, point in enumerate(vertices):
        struct.pack_into('<3f', out, 0x2038+i*12, *point)
    for i, point in enumerate(dummies):
        struct.pack_into('<3f', out, 0x5c+i*12, *point)
    out[0xe28:0xe2d] = b':body'
    return bytes(out)


def tire_image():
    points = ((-.4,-.2,-.3),(.4,-.2,-.3),(-.4,.2,.3),(.4,.2,.3))
    out = bytearray(0x2038 + len(points)*36)
    struct.pack_into('<4I',out,0,0x101015,0,0,len(points))
    struct.pack_into('<I',out,0x14,0)
    struct.pack_into('<I',out,0x34,len(points)*12)
    struct.pack_into('<I',out,0x2c,len(points)*24)
    struct.pack_into('<I',out,0x11c,1)
    struct.pack_into('<I',out,0x520,len(points))
    out[0xe28:0xe30]=b':PHwheel'
    for index,point in enumerate(points):
        for stream in range(3):
            struct.pack_into('<3f',out,0x2038+stream*len(points)*12+index*12,
                             *(value*(stream+1) for value in point))
    return bytes(out)


class ModelGroupCenteringTests(unittest.TestCase):
    def test_recenter_selected_bounds_then_apply_original_part_lift(self):
        source = image()
        result = prepare_model_group(PreparedModelGroup(
            (source,), (0,), (SelectedPart(0, 0, node_type=0x10),)))
        self.assertEqual(result.half_extents, (1., 2., 3.))
        self.assertEqual(result.center_translation, (-11., -22., -33.))
        self.assertEqual(result.selected_bounds,
                         ((10., 20., 30.), (12., 24., 36.)))
        shifted = result.group.models[0]
        self.assertEqual(struct.unpack_from('<3f', shifted, 0x120),
                         (-1., struct.unpack('<f', struct.pack('<f', -1.95))[0], -3.))
        self.assertEqual(struct.unpack_from('<3f', shifted, 0x5c), (-10., -20., -30.))

    def test_mirrored_selected_bounds_preserve_model_origin(self):
        result = prepare_model_group(PreparedModelGroup(
            (image(),), (0,), (SelectedPart(0, 0, flags=0x40),), owner_flags=0x40))
        self.assertEqual(result.selected_bounds,
                         ((8., 16., 24.), (10., 20., 30.)))
        self.assertEqual(result.half_extents, (1., 2., 3.))
        self.assertEqual(struct.unpack_from('<3f', result.group.models[0], 0x120),
                         (1., 2., 3.))

    def test_no_nonempty_selected_parts_has_zero_bounds(self):
        source = image(vertices=())
        result = prepare_model_group(PreparedModelGroup(
            (source,), (0,), (SelectedPart(0, 0),)))
        self.assertIsNone(result.selected_bounds)
        self.assertEqual(result.half_extents, (0., 0., 0.))
        self.assertEqual(result.group.models[0], source)

    def test_owner_flag_suppresses_suspension_mount_lift(self):
        result = prepare_model_group(PreparedModelGroup(
            (image(),), (0,), (SelectedPart(0, 0, node_type=0x12),), owner_flags=0x40))
        self.assertEqual(struct.unpack_from('<3f', result.group.models[0], 0x120),
                         (-1., -2., -3.))

    def test_invalid_reference_and_graph_are_rejected(self):
        group = PreparedModelGroup((image(),), (0,), (SelectedPart(0, 0),),
                                   secondary_model=0)
        with self.assertRaisesRegex(ValueError, 'reference part'):
            prepare_model_group(group)
        with self.assertRaisesRegex(ValueError, 'model index'):
            prepare_model_group(PreparedModelGroup((image(),), (2,), ()))

    def test_tire_component_scales_all_three_fce_streams(self):
        component = TireModelComponent(0x1adb1, 1, 0, 312.2344, 61.3257, 16.5636)
        result = prepare_tire_models((tire_image(),), (component,), 1)
        self.assertTrue(result.prepared)
        self.assertGreater(result.radius_m, 0.37)
        self.assertGreater(result.size_scales[0], 0)
        self.assertGreater(result.size_scales[1], 0)
        self.assertNotEqual(result.models[0], tire_image())

    def test_tire_component_selection_miss_preserves_model(self):
        source = tire_image()
        component = TireModelComponent(0x1adb1, 1, 0, 312., 60., 16.)
        result = prepare_tire_models((source,), (component,), 2)
        self.assertFalse(result.prepared)
        self.assertEqual(result.models, (source,))

    def test_rear_suspension_uses_exact_markers_and_tire_origin(self):
        tire = bytearray(tire_image())
        tire[0xe28:0xe28+len(b':PHtire')] = b':PHtire'
        tire[0xe28+len(b':PHtire')] = 0
        struct.pack_into('<3f', tire, 0x120, .71, .25, -.4)
        suspension = bytearray(tire_image())
        suspension[0xe28:0xe28+len(b':PHrearsusp')] = b':PHrearsusp'
        components = (TireModelComponent(0x1adb1, 3, 0),
                      TireModelComponent(0x3e9, 0, 1))
        result = prepare_rear_suspension_model((bytes(tire), bytes(suspension)),
                                                components)
        self.assertTrue(result.prepared)
        origin = struct.unpack_from('<3f', result.models[1], 0x120)
        self.assertEqual(origin[:2], (0., .25))
        self.assertEqual(struct.pack('<f', origin[2]), struct.pack('<f', -.4))
        self.assertAlmostEqual(result.scale_x, .71 / .4, places=6)

    def test_rear_suspension_marker_search_is_exact(self):
        tire = bytearray(tire_image())
        tire[0xe28:0xe28+len(b':PHtire')] = b':PHtire'
        tire[0xe28+len(b':PHtire')] = 0
        suspension = bytearray(tire_image())
        suspension[0xe28:0xe28+17] = b':PHrearsusp-extra'
        components = (TireModelComponent(0x1adb1, 4, 0),
                      TireModelComponent(0x3e9, 0, 1))
        result = prepare_rear_suspension_model((bytes(tire), bytes(suspension)),
                                                components)
        self.assertFalse(result.prepared)

    def test_vehicle_model_pipeline_runs_tires_then_suspension_then_centering(self):
        body = image()
        tire = bytearray(tire_image())
        tire_name = b':PHtire'
        tire[0xe28:0xe28+len(tire_name)] = tire_name
        tire[0xe28+len(tire_name)] = 0
        suspension = bytearray(tire_image())
        suspension_name = b':PHrearsusp'
        suspension[0xe28:0xe28+len(suspension_name)] = suspension_name
        suspension[0xe28+len(suspension_name)] = 0
        components = (TireModelComponent(0, 0, 0),
                      TireModelComponent(0x1adb1, 3, 1, 300., 60., 16.),
                      TireModelComponent(0x3e9, 0, 2))
        group = PreparedModelGroup((body, bytes(tire), bytes(suspension)),
            (0, 1, 2), (SelectedPart(0,0), SelectedPart(1,0),
                         SelectedPart(2,0)), owner_flags=0x40)
        result = prepare_vehicle_model_group(group, components)
        self.assertEqual(tuple(stage.prepared for stage in result.tire_results),
                         (False, False, False, True))
        self.assertTrue(result.suspension_result.prepared)
        self.assertEqual(len(result.result.group.models), 3)
        self.assertTrue(all(value > 0 for value in result.result.half_extents))


if __name__ == '__main__':
    unittest.main()
