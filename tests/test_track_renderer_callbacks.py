import unittest

from client.track_renderer_callbacks import (transform_render_position,
                                              transform_render_positions)


class TrackRendererCallbackTests(unittest.TestCase):
    def test_viewport_maps_center_and_preserves_reciprocal_depth(self):
        x,y,z,w=transform_render_position((0,0,10))
        self.assertEqual((x,y),(319.5,239.5))
        self.assertAlmostEqual(w,0.1,places=7)
        self.assertAlmostEqual(z,(10-1.0001)*0.00004,places=8)

    def test_zero_depth_uses_original_fallback_factor(self):
        self.assertEqual(transform_render_position((0,0,0))[3],10000.0)

    def test_transforms_multiple_vertices(self):
        rows=transform_render_positions(((0,0,10),(1,-1,2)))
        self.assertEqual(len(rows),2)
        self.assertAlmostEqual(rows[1][0],479.25,places=5)
        self.assertAlmostEqual(rows[1][1],399.25,places=5)

    def test_rejects_invalid_shapes(self):
        with self.assertRaises(ValueError):transform_render_position((1,2))
        with self.assertRaises(ValueError):transform_render_position((1,2,3),(1,2))


if __name__ == '__main__':unittest.main()
