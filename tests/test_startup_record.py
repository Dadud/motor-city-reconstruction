"""Integration of recovered decoded-scene area into owner startup records."""
import math
import struct
import unittest

from client.fce import Model, Part, Triangle
from client.raster_scene import RasterSceneNode, raster_nodes_from_render_list
from client.render_list import RenderRecord, build_render_list
from client.scene_area_measure import scene_area_from_nodes
from client.startup_record import construct_startup_record
from tools.startup_record_oracle import configuration, model_image, owner_image


class StartupRecordTests(unittest.TestCase):
    def scene(self):
        model = Model((Part('body', (0., 0., 0.),
            ((-2., -1., 0.), (2., -1., 0.), (0., 3., 0.)),
            ((0., 0., 1.),)*3,
            (Triangle((0, 1, 2), (0., 0., 1., 0., .5, 1.), 0, 0),)),),
            0x101014)
        return (RasterSceneNode(model, 0, 0),)

    def test_decoded_scene_nodes_feed_the_recovered_area_field(self):
        cfg = configuration(0, 4)
        owner = owner_image(0, 2.05)
        source = self.scene()
        render_list = build_render_list((RenderRecord(
            (0, 0, 0, source[0].surface_id, 0, source[0].mesh_type, 0, 0, 0)),))
        nodes = raster_nodes_from_render_list((source[0].model,), render_list)
        area = scene_area_from_nodes(nodes)
        self.assertGreater(area, 0.)
        actual, code = construct_startup_record(owner, cfg, model_image(False),
                                                scene_nodes=nodes)
        expected, expected_code = construct_startup_record(owner, cfg,
            model_image(False), area_query=area)
        self.assertEqual(code, expected_code)
        self.assertEqual(actual, expected)
        self.assertEqual(struct.unpack_from('<f', actual, 0xd4)[0], area)
        self.assertTrue(all(math.isfinite(value) for value in
            struct.unpack_from('<4f', actual, 0xd4)))

    def test_area_source_is_required_and_exclusive(self):
        cfg = configuration(0, 4)
        owner = owner_image(0, 2.05)
        with self.assertRaisesRegex(ValueError, 'required'):
            construct_startup_record(owner, cfg, model_image(False))
        with self.assertRaisesRegex(ValueError, 'not both'):
            construct_startup_record(owner, cfg, model_image(False), 1.,
                                     scene_nodes=self.scene())
