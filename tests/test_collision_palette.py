import struct
import unittest

from client.collision_palette import adjust_color_records, adjust_color_words


class CollisionPaletteTests(unittest.TestCase):
    def test_percentages_scale_rgb_and_preserve_alpha(self):
        image = bytearray(struct.pack('<I', 0x7f804020))
        adjust_color_words(image, 1, (50, 125, 200))
        self.assertEqual(struct.unpack('<I', image)[0], 0x7f406fff)

    def test_identity_channel_and_zero_count(self):
        image = bytearray(struct.pack('<2I', 0xff123456, 0x80402010))
        before = bytes(image)
        adjust_color_words(image, 2, (100, 100, 100))
        self.assertEqual(bytes(image), before)
        adjust_color_words(image, 0, (0, 0, 0))
        self.assertEqual(bytes(image), before)

    def test_color_record_groups(self):
        first = bytearray(struct.pack('<2I', 0xff808080, 0x01020304))
        second = bytearray(struct.pack('<I', 0x10203040))
        result = adjust_color_records(((2, first), (1, second)), (0, 100, 200))
        self.assertEqual(result[0][1], first)
        self.assertEqual(struct.unpack('<2I', first), (0xff0080ff, 0x010003ff))
        self.assertEqual(struct.unpack('<I', second)[0], 0x100030ff)

    def test_signed_percentage_uses_truncated_division_and_low_byte(self):
        image = bytearray(struct.pack('<I', 0x7f804020))
        adjust_color_words(image, 1, (-1, 150, 0x7fffffff))
        self.assertEqual(struct.unpack('<I', image)[0] & 0xff000000, 0x7f000000)
        # The signed red product truncates toward zero before byte masking.
        self.assertEqual((struct.unpack('<I', image)[0] >> 16) & 0xff, 0xff)

    def test_rejects_unsupported_color_inputs(self):
        with self.assertRaises(ValueError):
            adjust_color_words(bytearray(4), 2, (100, 100, 100))
        with self.assertRaises(ValueError):
            adjust_color_words(bytearray(4), 1, (100, 1 << 31, 100))


if __name__ == '__main__':
    unittest.main()
