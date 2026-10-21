import unittest

from client.fce import Model, Part, Triangle
from client.raster_fill import rasterize_projected_triangle
from client.raster_scene import (RasterMesh, RasterSceneNode,
                                 raster_meshes_from_nodes,
                                 raster_nodes_from_render_list,
                                 rasterize_scene_geometry)
from client.render_list import RenderRecord, build_render_list
from client.scene_area_measure import scene_area_from_nodes


class RasterSceneTests(unittest.TestCase):
    def test_traverses_faces_applies_surface_mirror_and_unions_pixels(self):
        mesh = RasterMesh(
            vertices=((1, 1, 0), (9, 1, 0), (5, 9, 0),
                      (2, 2, 0), (8, 2, 0), (5, 7, 0)),
            triangles=((0, 1, 2), (3, 4, 5)),
            position=(0, 0, 0))
        mirrored = RasterMesh(
            vertices=((-1, 1, 0), (-9, 1, 0), (-5, 9, 0)),
            triangles=((0, 1, 2),), position=(10, 0, 0), mesh_type=5)
        skipped = RasterMesh(
            vertices=(), triangles=(), mesh_type=16)
        result = rasterize_scene_geometry((mesh, mirrored, skipped), (0, 10), (0, 10))
        expected = bytearray(len(result))
        for triangle in (((1, 1), (9, 1), (5, 9)),
                         ((2, 2), (8, 2), (5, 7)),
                         ((9, 1), (1, 1), (5, 9))):
            mask = rasterize_projected_triangle(triangle, (0, 10), (0, 10))
            for index, value in enumerate(mask):
                if value:
                    expected[index] = 1
        self.assertEqual(result, bytes(expected))

    def test_rejects_invalid_face_indices(self):
        mesh = RasterMesh(vertices=((0, 0, 0),), triangles=((0, 1, 0),))
        with self.assertRaises(ValueError):
            rasterize_scene_geometry((mesh,), (0, 1), (0, 1))

    def test_adapts_decoded_fce_parts_from_scene_nodes(self):
        part = Part('body', (2, 3, 4), ((0, 0, 0), (8, 0, 0), (4, 8, 0)),
                    ((0, 0, 1),) * 3,
                    (Triangle((0, 1, 2), (0, 0, 0, 0, 0, 0), 0, 0),))
        model = Model((part,), 0x101014)
        nodes = (RasterSceneNode(model, 0, 5),
                 RasterSceneNode(None, 0, 0),
                 RasterSceneNode(model, 99, 16))
        meshes = raster_meshes_from_nodes(nodes)
        self.assertEqual(meshes[0].vertices, part.vertices)
        self.assertEqual(meshes[0].triangles, ((0, 1, 2),))
        self.assertEqual(meshes[0].position, part.origin)
        self.assertFalse(meshes[1].has_model)
        self.assertEqual(meshes[2].mesh_type, 16)

    def test_rejects_scene_node_surface_outside_fce_model(self):
        model = Model((), 0x101014)
        with self.assertRaises(ValueError):
            raster_meshes_from_nodes((RasterSceneNode(model, 0, 0),))

    def test_render_list_records_feed_the_projected_area_path(self):
        parts = tuple(Part(f'part{i}', (i * 2., 0., 0.),
            ((0., 0., 0.), (2., 0., 0.), (1., 3., 0.)),
            ((0., 0., 1.),) * 3,
            (Triangle((0, 1, 2), (0.,) * 6, 0, 0),)) for i in range(2))
        model = Model(parts, 0x101014)
        records = build_render_list((
            RenderRecord((0, 0, 0, 1, 1, 5, 0, 0, 0)),
            RenderRecord((0, 0, 0, 0, 1, 0, 0, 0, 0))))
        nodes = raster_nodes_from_render_list((model,), records)
        self.assertEqual(tuple((n.surface_id, n.mesh_type) for n in nodes),
                         ((1, 5), (0, 0)))
        expected = (RasterSceneNode(model, 1, 5), RasterSceneNode(model, 0, 0))
        self.assertEqual(scene_area_from_nodes(nodes), scene_area_from_nodes(expected))

    def test_render_list_adapter_rejects_missing_models_and_surfaces(self):
        model = Model((), 0x101014)
        invalid_model = build_render_list((RenderRecord((0, 1, 0, 0, 0, 0, 0, 0, 0)),))
        with self.assertRaisesRegex(ValueError, 'unknown model'):
            raster_nodes_from_render_list((model,), invalid_model)
        invalid_surface = build_render_list((RenderRecord((0, 0, 0, 0, 0, 0, 0, 0, 0)),))
        with self.assertRaisesRegex(ValueError, 'surface'):
            raster_nodes_from_render_list((model,), invalid_surface)


if __name__ == '__main__':
    unittest.main()
