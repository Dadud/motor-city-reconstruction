import unittest

from client.fce import Model, Part, Triangle
from client.raster_scene import RasterMesh, RasterSceneNode
from client.scene_area_measure import scene_area_from_geometry, scene_area_from_nodes


class SceneAreaMeasureTests(unittest.TestCase):
    def test_reproduces_projected_density_formula_for_triangle(self):
        mesh = RasterMesh(vertices=((1,1,0),(9,1,0),(5,9,0)),
                          triangles=((0,1,2),))
        self.assertEqual(scene_area_from_geometry((mesh,)), 31.967321395874023)

    def test_returns_zero_when_raster_is_disabled_or_no_surface_contributes(self):
        triangle = RasterMesh(vertices=((1,1,0),(9,1,0),(5,9,0)),
                              triangles=((0,1,2),))
        skipped = RasterMesh(vertices=(),triangles=(),mesh_type=16)
        absent = RasterMesh(vertices=((1,1,0),(9,1,0),(5,9,0)),
                            triangles=((0,1,2),),has_model=False)
        malformed = RasterMesh(vertices=((0,0,0),),triangles=((0,1,0),))
        self.assertEqual(scene_area_from_geometry((triangle,),raster_enabled=False),0.0)
        self.assertEqual(scene_area_from_geometry((malformed,),raster_enabled=False),0.0)
        self.assertEqual(scene_area_from_geometry((skipped,absent)),0.0)

    def test_returns_zero_for_degenerate_projected_bounds(self):
        line = RasterMesh(vertices=((2,1,0),(2,5,0),(2,9,0)),
                          triangles=((0,1,2),))
        self.assertEqual(scene_area_from_geometry((line,)),0.0)

    def test_area_accepts_selected_decoded_fce_surfaces(self):
        part = Part('body', (1, 1, 0), ((0, 0, 0), (8, 0, 0), (4, 8, 0)),
                    ((0, 0, 1),) * 3,
                    (Triangle((0, 1, 2), (0, 0, 0, 0, 0, 0), 0, 0),))
        model = Model((part,), 0x101014)
        node = RasterSceneNode(model, 0, 0)
        direct = RasterMesh(part.vertices, ((0, 1, 2),), part.origin)
        self.assertEqual(scene_area_from_nodes((node,)),
                         scene_area_from_geometry((direct,)))


if __name__ == '__main__':
    unittest.main()
