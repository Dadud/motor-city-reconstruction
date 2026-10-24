import unittest

from client.track_surface_query import cached_quad_hit


class TrackSurfaceQueryTests(unittest.TestCase):
    def setUp(self):
        self.quad=((0.,0.,0.),(10.,1.,0.),(10.,2.,10.),(0.,3.,10.))

    def test_cached_quad_returns_binary32_query_position(self):
        point=(3.25,7.5,4.5)
        self.assertEqual(cached_quad_hit(point,self.quad),point)

    def test_cached_quad_rejects_point_outside(self):
        self.assertIsNone(cached_quad_hit((11.,0.,5.),self.quad))


if __name__=='__main__':
    unittest.main()
