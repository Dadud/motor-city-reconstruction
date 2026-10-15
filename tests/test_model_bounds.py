import math
from types import SimpleNamespace
import unittest
from client.model_bounds import transformed_part_bounds


class ModelBoundsTests(unittest.TestCase):
    def test_latest_equal_vertex_preserves_negative_zero(self):
        part = SimpleNamespace(origin=(-0., -0., -0.), vertices=[(0.,0.,0.),(-0.,-0.,-0.)])
        result = transformed_part_bounds(part)
        self.assertTrue(all(math.copysign(1., v) < 0 for v in result.minimum+result.maximum))

    def test_mirror_applies_before_origin_translation(self):
        part = SimpleNamespace(origin=(10.,20.,30.), vertices=[(2.,3.,4.),(-5.,-6.,-7.)])
        result = transformed_part_bounds(part, mirrored=True)
        self.assertEqual(result.minimum, (8.,14.,23.))
        self.assertEqual(result.maximum, (15.,23.,34.))
        self.assertEqual(part.vertices[0], (2.,3.,4.))

    def test_empty_and_nonfinite_geometry(self):
        self.assertIsNone(transformed_part_bounds(SimpleNamespace(origin=(0.,0.,0.),vertices=[])))
        with self.assertRaises(ValueError):
            transformed_part_bounds(SimpleNamespace(origin=(0.,0.,0.), vertices=[(math.inf,0.,0.)]))


if __name__ == '__main__':
    unittest.main()
