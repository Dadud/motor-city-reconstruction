import unittest

import struct

from client.track_surface_query import cached_quad_hit,nearest_track_neighbor


class TrackSurfaceQueryTests(unittest.TestCase):
    def setUp(self):
        self.quad=((0.,0.,0.),(10.,1.,0.),(10.,2.,10.),(0.,3.,10.))

    def test_cached_quad_returns_binary32_query_position(self):
        point=(3.25,7.5,4.5)
        self.assertEqual(cached_quad_hit(point,self.quad),point)

    def test_cached_quad_rejects_point_outside(self):
        self.assertIsNone(cached_quad_hit((11.,0.,5.),self.quad))

    def test_neighbor_search_wraps_and_preserves_ties(self):
        rows=[bytearray(0x54) for _ in range(9)]
        for row in rows:
            struct.pack_into('<3f',row,0,20.,0.,20.)
        struct.pack_into('<3f',rows[3],0,0.,0.,0.)
        frozen=tuple(bytes(row) for row in rows)
        self.assertEqual(nearest_track_neighbor((0.,0.,0.),frozen,8),3)
        struct.pack_into('<3f',rows[0],0,0.,0.,0.)
        self.assertEqual(nearest_track_neighbor((0.,0.,0.),
                         tuple(bytes(row) for row in rows),0),0)


if __name__=='__main__':
    unittest.main()
