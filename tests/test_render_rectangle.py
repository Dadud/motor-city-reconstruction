import unittest

from client.render_rectangle import (
    plan_filled_rectangle_vertices, plan_rectangle_border_edges)
from client.render_clip_code import RenderClipBounds
from client.render_quad_dispatch import (
    dispatch_first_fan_triangle, dispatch_inside_quad, dispatch_quad,
    dispatch_second_fan_triangle)
from client.render_polygon_clip import reject_triangle_on_shared_near_plane
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

    def test_inside_quad_dispatch_adjusts_depth_and_preserves_payload(self):
        word=lambda value: struct.unpack('<I',struct.pack('<f',value))[0]
        vertices=tuple((word(float(i)),word(2.),0x3f7fff00,word(w),
                        i+1,0,tail1,tail2)
                       for i,(w,tail1,tail2) in enumerate((
                           (0.25,0x12345678,9),(0.75,10,11),
                           (1.25,12,13),(-1.,14,15))))
        result=dispatch_inside_quad(vertices,1.,99.)
        self.assertEqual(tuple(v[2] for v in result.vertices),
                         (word(.75),word(.25),word(99.),word(99.)))
        self.assertEqual(result.callback_words,result.vertices)
        self.assertEqual(tuple(v[6:] for v in result.vertices),
                         ((0x12345678,9),(10,11),(12,13),(14,15)))

    def test_inside_quad_preserves_and_dispatches_canonical_quiet_nan(self):
        vertices=[list((0,0,0,0,0,0,0,0)) for _ in range(4)]
        vertices[2][7]=0xffc00000
        result=dispatch_inside_quad(vertices,1.,99.)
        self.assertEqual(result.callback_words,result.vertices)

    def test_positive_nan_uses_native_ordered_depth_branch(self):
        vertices=[list((0,0,0,0,0,0,0,0)) for _ in range(4)]
        vertices[0][3]=0x7fcced5b
        result=dispatch_inside_quad(vertices,10.,99.)
        self.assertEqual(result.vertices[0][2],0x7fcced5b)

    def test_quad_router_composes_clipper_and_direct_fan_requests(self):
        vertices=tuple((index,10,0,0x3f000000,index,0,20+index,30+index)
                       for index in range(4))
        vertices=(vertices[0],vertices[1][:5]+(1,)+vertices[1][6:],
                  vertices[2],vertices[3])
        trace=dispatch_quad(vertices)
        self.assertIsNone(trace.quad_callback)
        self.assertEqual(trace.clip_requests,(((0,1,2),(0,1,0),1),))
        self.assertEqual(len(trace.triangle_callbacks),1)
        self.assertEqual(tuple(vertex[0] for vertex in
                               trace.triangle_callbacks[0]),(0,2,3))

    def test_quad_router_rejects_a_clip_bit_shared_by_every_corner(self):
        vertices=tuple((0,0,0,0,0,4,0,0) for _ in range(4))
        trace=dispatch_quad(vertices)
        self.assertEqual((trace.quad_callback,trace.triangle_callbacks,
                          trace.clip_requests),(None,(),()))

    def test_first_fan_triangle_emits_when_last_corner_is_outside(self):
        word=lambda value: struct.unpack('<I',struct.pack('<f',value))[0]
        vertices=tuple((word(float(i)),word(2.),0x3f7fff00,word(.25),
                        i+1,0,0x100+i,0x200+i)
                       for i in range(4))
        vertices=vertices[:3]+(vertices[3][:5]+(0x10,)+vertices[3][6:],)
        result=dispatch_first_fan_triangle(vertices,1.,99.)
        self.assertEqual(result.callback_words,result.vertices)
        self.assertEqual(tuple(v[2] for v in result.vertices),(word(.75),)*3)
        self.assertEqual(tuple(v[4] for v in result.vertices),(1,2,3))

    def test_second_fan_triangle_emits_when_second_corner_is_outside(self):
        vertices=tuple((0,0,0,0,0,0,10+i,20+i) for i in range(4))
        vertices=(vertices[0],vertices[1][:5]+(0x10,)+vertices[1][6:],
                  vertices[2],vertices[3])
        result=dispatch_second_fan_triangle(vertices,1.,99.)
        self.assertEqual(tuple(v[6:] for v in result.callback_words),
                         ((10,20),(12,22),(13,23)))

    def test_first_fan_triangle_suppresses_canonical_nan_payload(self):
        vertices=tuple((0,0,0,0,0,0,0,0) for _ in range(3))
        outside=(0,0,0,0,0,0x10,0,0)
        vertices=vertices+(outside,)
        vertices=(vertices[0],vertices[1][:7]+(0xffc00000,),
                  vertices[2],vertices[3])
        result=dispatch_first_fan_triangle(vertices,1.,99.)
        self.assertIsNone(result.callback_words)

    def test_input_words_are_range_checked(self):
        with self.assertRaises(ValueError):
            plan_rectangle_border_edges(0,0,1,1,0,(1,2,3,0x100000000))

    def test_polygon_clipper_shared_near_plane_reject(self):
        self.assertEqual(reject_triangle_on_shared_near_plane((1,0x11,0x21)),
                         0xffffffff)

    def test_polygon_clipper_does_not_claim_partial_or_other_plane_cases(self):
        self.assertIsNone(reject_triangle_on_shared_near_plane((1,0,1)))
        with self.assertRaises(ValueError):
            reject_triangle_on_shared_near_plane((1,1,1),0x04)


if __name__=='__main__':
    unittest.main()
