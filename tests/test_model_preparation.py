import struct
import unittest
from client.model_preparation import part_half_extents,scale_part_streams,align_secondary_model
from tools.model_preparation_oracle import image


class ModelPreparationTests(unittest.TestCase):
    def test_empty_invalid_and_nonempty_part(self):
        b=image()
        self.assertIsNone(part_half_extents(b,-1));self.assertIsNone(part_half_extents(b,3))
        self.assertIsNone(part_half_extents(b,2))
        self.assertTrue(all(v>0 for v in part_half_extents(b,0)))

    def test_invalid_scale_does_not_modify(self):
        b=image();before=bytes(b)
        scale_part_streams(b,-1,(2,3,4));self.assertEqual(b,before)
        with self.assertRaises(ValueError):scale_part_streams(b,0,(float('nan'),1,1))
        self.assertEqual(b,before)

    def test_aliased_streams_are_scaled_three_times(self):
        b=image(alias=True);initial=struct.unpack_from('<3f',b,0x2038)
        scale_part_streams(b,0,(2,2,2))
        self.assertEqual(struct.unpack_from('<3f',b,0x2038),tuple(v*8 for v in initial))

    def test_alignment_uses_first_case_sensitive_substring(self):
        b=image(names=(b'_w',b'body_W_detail',b'_W'));ref=image(4)
        initial=bytes(b);self.assertTrue(align_secondary_model(b,ref,0))
        self.assertEqual(struct.unpack_from('<f',b,0x120+12)[0],struct.unpack_from('<f',ref,0x120)[0])
        self.assertEqual(b[0x2038:],initial[0x2038:])
        self.assertNotEqual(b[0x5c:0x74],initial[0x5c:0x74])

    def test_alignment_no_matching_name_preserves_entire_image(self):
        b=image(names=(b'_w',b'body',b'tail'));before=bytes(b)
        self.assertFalse(align_secondary_model(b,image(2),0));self.assertEqual(b,before)

    def test_bounded_corruption(self):
        b=image();struct.pack_into('<I',b,0x520,1_000_001)
        with self.assertRaises(ValueError):part_half_extents(b,0)
        b=image();b[0xe28:0xe68]=b'x'*64
        with self.assertRaises(ValueError):align_secondary_model(b,image(2),0)
