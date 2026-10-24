import unittest

from client.render_rectangle import (
    plan_filled_rectangle_vertices, plan_rectangle_border_edges)
from client.render_clip_code import RenderClipBounds
import struct


class RenderRectangleTests(unittest.TestCase):
    def test_border_edges_follow_native_order_and_cycle_attributes(self):
        edges=plan_rectangle_border_edges(10,20,100,60,2,
                                          (0x11,0x22,0x33,0x44))
        self.assertEqual(tuple((edge.x1,edge.y1,edge.x2,edge.y2,
                                edge.attribute1,edge.attribute2)
                               for edge in edges),(
            (10,20,108,20,0x11,0x22),
            (108,20,108,78,0x22,0x33),
            (108,78,10,78,0x33,0x44),
            (10,78,10,20,0x44,0x11),
        ))

    def test_empty_pre_inset_rectangle_has_no_edges(self):
        self.assertEqual(plan_rectangle_border_edges(
            3,4,0,0,2,(1,2,3,4)),())

    def test_geometry_uses_signed_x86_wraparound(self):
        edges=plan_rectangle_border_edges(
            0x7fffffff,0,2,2,0,(1,2,3,4))
        self.assertEqual((edges[0].x2,edges[2].x2),(-0x7fffffff,0x7fffffff))

    def test_filled_vertices_match_native_corner_order_and_fields(self):
        bounds=RenderClipBounds(-1150000000,1150000000,
                               -1150000000,1150000000,1065353216,0)
        vertices=plan_filled_rectangle_vertices(
            10,20,100,60,(0x11,0x22,0x33,0x44),bounds,
            opaque_words=((0xaabbccdd,2,3),(4,5,6),(7,8,9),(10,11,12)))
        floats=lambda word: struct.unpack('<f',struct.pack('<I',word))[0]
        self.assertEqual(tuple((floats(v.x_word),floats(v.y_word))
                               for v in vertices),
                         ((10.,20.),(110.,20.),(110.,80.),(10.,80.)))
        self.assertEqual(tuple(v.attribute_word for v in vertices),
                         (0x11,0x22,0x33,0x44))
        self.assertEqual(tuple(v.clip_tail_words[0] for v in vertices),
                         (0xaabbcc02,0x00000002,0x00000002,0x00000002))
        self.assertTrue(all((v.z_word,v.w_word)==
                            (0x3f7fff00,0x37800080) for v in vertices))
        self.assertTrue(all(v.clip_code == 0x02 for v in vertices))

    def test_filled_vertices_compute_native_clip_codes(self):
        bounds=RenderClipBounds(-10,10,-10,10,0x3f800000,0)
        vertices=plan_filled_rectangle_vertices(
            20,0,5,5,(1,2,3,4),bounds,
            opaque_words=((0,0,0),)*4)
        self.assertEqual(tuple(v.clip_code for v in vertices),
                         (0x22,0x22,0x2a,0x2a))

    def test_input_words_are_range_checked(self):
        with self.assertRaises(ValueError):
            plan_rectangle_border_edges(0,0,1,1,0,(1,2,3,0x100000000))


if __name__=='__main__':
    unittest.main()
