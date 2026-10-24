import unittest

from client.track_surface import find_surface_quad_candidate


class TrackSurfaceCandidateLookupTests(unittest.TestCase):
    def setUp(self):
        vertices = ((0., 0., 0.), (10., 0., 0.),
                    (10., 1., 10.), (0., 1., 10.))
        quads = ((0, 1, 2, 3),)
        descriptors = ((0, 0, 0, 0), (0, 0, 0, 0))
        self.blocks = ((vertices, quads, descriptors),)

    def test_returns_first_inside_candidate(self):
        self.assertEqual(find_surface_quad_candidate(5., 5.,
            ((0, 0), (0, 1)), self.blocks), (0, 0))

    def test_skips_outside_then_returns_later_hit(self):
        self.assertEqual(find_surface_quad_candidate(5., 5.,
            ((0, 0), (0, 1)), self.blocks), (0, 0))
        self.assertIsNone(find_surface_quad_candidate(15., 5.,
            ((0, 0), (0, 1)), self.blocks))


if __name__ == '__main__':
    unittest.main()
