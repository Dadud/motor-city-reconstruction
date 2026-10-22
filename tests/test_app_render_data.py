import unittest

from client.app import _part_color
from client.fce import Part


class AppRenderDataTests(unittest.TestCase):
    def test_packed_native_argb_vertex_color_becomes_rgba(self):
        part = Part('color', (0, 0, 0), ((0, 0, 0),), ((0, 1, 0),), (),
                    (0x7f406fff,))
        self.assertEqual(_part_color(part, 0),
                         (64 / 255, 111 / 255, 255 / 255, 127 / 255))

    def test_uncolored_parts_use_white_tint(self):
        part = Part('plain', (0, 0, 0), ((0, 0, 0),), ((0, 1, 0),), ())
        self.assertEqual(_part_color(part, 0), (1, 1, 1, 1))

    def test_misaligned_color_arrays_are_rejected(self):
        part = Part('bad', (0, 0, 0), ((0, 0, 0),), ((0, 1, 0),), (),
                    (0xffffffff, 0xffffffff))
        with self.assertRaisesRegex(ValueError, 'count disagrees'):
            _part_color(part, 0)


if __name__ == '__main__':
    unittest.main()
