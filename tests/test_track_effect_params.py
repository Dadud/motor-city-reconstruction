import math
import struct
import unittest

from client.track_effect_params import BLOCK_SIZE, prepare_track_effect_params


class TrackEffectParameterTests(unittest.TestCase):
    def test_updates_normalized_fields_and_preserves_unrelated_bytes(self):
        block = bytearray(b'\xa5' * BLOCK_SIZE)
        struct.pack_into('<i', block, 0xC0D8, 4)
        struct.pack_into('<i', block, 0xC0C8, 20)
        struct.pack_into('<i', block, 0xC0D0, 21)
        struct.pack_into('<f', block, 0xC118, 0.0)
        struct.pack_into('<f', block, 0xC11C, -0.0)
        struct.pack_into('<i', block, 0xC134, 90)
        struct.pack_into('<i', block, 0xC130, 5000)
        result = prepare_track_effect_params(block)
        self.assertIs(result, block)
        self.assertEqual(struct.unpack_from('<f', block, 0xC0DC)[0], 0.25)
        self.assertEqual(struct.unpack_from('<i', block, 0xC0D0)[0], 20)
        self.assertEqual(struct.unpack_from('<f', block, 0xC118)[0], 1.0)
        self.assertEqual(struct.unpack_from('<f', block, 0xC11C)[0], 1.0)
        self.assertEqual(block[:0xC0C8], b'\xa5' * 0xC0C8)
        self.assertEqual(block[0xC0CC:0xC0D0], b'\xa5' * 4)
        self.assertEqual(block[0xC120:0xC130], b'\xa5' * 0x10)

    def test_zero_count_keeps_reciprocal_and_nan_factors_are_replaced(self):
        block = bytearray(BLOCK_SIZE)
        struct.pack_into('<f', block, 0xC0DC, 7.0)
        struct.pack_into('<f', block, 0xC118, math.nan)
        struct.pack_into('<f', block, 0xC11C, math.nan)
        prepare_track_effect_params(block)
        self.assertEqual(struct.unpack_from('<f', block, 0xC0DC)[0], 7.0)
        self.assertEqual(struct.unpack_from('<f', block, 0xC118)[0], 1.0)
        self.assertEqual(struct.unpack_from('<f', block, 0xC11C)[0], 1.0)

    def test_rejects_nonmutable_or_short_block(self):
        with self.assertRaises(TypeError):
            prepare_track_effect_params(bytes(BLOCK_SIZE))
        with self.assertRaises(ValueError):
            prepare_track_effect_params(bytearray(BLOCK_SIZE - 1))


if __name__ == '__main__':
    unittest.main()
