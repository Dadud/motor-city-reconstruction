import struct
import unittest

from client.render_clip_code import RenderClipBounds
from client.render_segment_clip import SegmentClipBounds
from client.render_segment_construct import construct_render_segment


def _word(value):
    return struct.unpack('<i',struct.pack('<f',value))[0]


class RenderSegmentConstructionTests(unittest.TestCase):
    def setUp(self):
        self.clip_codes=RenderClipBounds(
            _word(-100.),_word(100.),_word(-100.),_word(100.),
            _word(1.),_word(1.))
        self.segment_bounds=SegmentClipBounds(
            10.,0.0016666667,-100.,100.,-100.,100.,0xcf)

    def test_constructs_two_native_endpoint_records_and_preserves_raw_fields(self):
        result=construct_render_segment(
            1,2,30,40,0x7fc12345,0xffffffff,self.clip_codes,
            self.segment_bounds,opaque_words=(0xdeadbeef,0xaabbccdd))
        self.assertEqual(result.first_words,
                         (0x3f800000,0x40000000,0x3f7fff00,0x37800080,
                          0x7fc12345,0xdeadbeef))
        self.assertEqual(result.second_words,
                         (0x41f00000,0x42200000,0x3f7fff00,0x37800080,
                          0xffffffff,0xaabbccdd))
        self.assertEqual((result.first_code,result.second_code),(0,0))
        self.assertEqual(result.clipped_words,
                         (result.first_words,result.second_words))

    def test_clipping_changes_xy_and_preserves_attribute_words(self):
        result=construct_render_segment(
            200,0,0,0,0xff112233,0x80112233,self.clip_codes,
            self.segment_bounds,opaque_words=(1,2))
        self.assertIsNotNone(result.clipped_words)
        self.assertEqual(result.clipped_words[0][0],_word(100.))
        self.assertEqual(result.clipped_words[0][4:],(0xff112233,1))
        self.assertEqual(result.clipped_words[1][4:],(0x80112233,2))

    def test_common_outcode_rejects_without_a_draw_event(self):
        result=construct_render_segment(
            150,0,200,20,1,2,self.clip_codes,self.segment_bounds,
            opaque_words=(3,4))
        self.assertEqual(result.first_code & result.second_code,0x20)
        self.assertIsNone(result.clipped_words)

    def test_parallel_outside_segment_uses_native_ieee_division_semantics(self):
        result=construct_render_segment(
            -7,-8,-100,-173,1,2,self.clip_codes,self.segment_bounds,
            opaque_words=(3,4))
        self.assertIsNotNone(result.clipped_words)

    def test_stack_residue_words_are_required_and_validated(self):
        with self.assertRaises(ValueError):
            construct_render_segment(0,0,1,1,1,2,self.clip_codes,
                                     self.segment_bounds,opaque_words=(1,))


if __name__=='__main__':
    unittest.main()
