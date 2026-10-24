import unittest

from client.track_surface import surface_color_from_candidate


class TrackSurfaceColorQueryTests(unittest.TestCase):
    def test_no_candidate_returns_native_sentinel(self):
        self.assertEqual(surface_color_from_candidate(None, ()), 0xffffffff)

    def test_resolves_descriptor_then_averages_vertex_colors(self):
        block = ((), ((0, 1, 2, 3),), ((0, 0, 0, 0),),
                 (0xff000000, 0xff04080c, 0xff081018, 0xff0c1824))
        self.assertEqual(surface_color_from_candidate((0, 0), (block,)),
                         0xff060c12)


if __name__ == '__main__':
    unittest.main()
