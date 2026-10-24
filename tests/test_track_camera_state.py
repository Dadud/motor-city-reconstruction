import struct
import unittest

from client.track_surface import build_track_camera_state


class TrackCameraStateTests(unittest.TestCase):
    def setUp(self):
        self.row = (10., 20., 30., 1., 2., 3., 4., 5., 6.,
                    0., 1., 0., 2., 3.) + (0.,) * 7

    def test_forward_and_reverse_offsets_follow_row_normal(self):
        forward = build_track_camera_state(self.row, 17, 1, 2.)
        reverse = build_track_camera_state(self.row, 17, 0, 2.)
        self.assertEqual(struct.unpack_from('<3f', forward, 0x0c), (10., 24.5, 30.))
        self.assertEqual(struct.unpack_from('<3f', reverse, 0x0c), (10., 20.5, 30.))

    def test_neutral_mode_and_track_index_fields(self):
        state = build_track_camera_state(self.row, 19, 2, -1.)
        self.assertEqual(struct.unpack_from('<3f', state, 0x0c), (10., 19., 30.))
        self.assertEqual(struct.unpack_from('<II', state, 0x44), (19, 2))
        self.assertEqual(struct.unpack_from('<f', state, 0x3c), (1.,))


if __name__ == '__main__':
    unittest.main()
