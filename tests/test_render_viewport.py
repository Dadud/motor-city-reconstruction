import struct
import unittest

from client.render_viewport import (RenderViewport, classify_render_position,
                                    configure_render_viewport,
                                    prepare_render_viewport_request,
                                    RenderViewportRequest,
                                    set_alternate_render_bounds,
                                    set_alternate_render_viewport_words)


class RenderViewportTests(unittest.TestCase):
    def test_sets_derived_bounds_and_clears_only_the_strided_field(self):
        records=[bytearray(bytes([0xa5])*32) for _ in range(100)]
        state=configure_render_viewport(
            RenderViewport(10.,20.,640.,480.,.1,1000.),records)
        self.assertEqual((state.x_min,state.y_min,state.x_max,state.y_max),
                         (10.,20.,650.,500.))
        self.assertEqual(state.reciprocal_w_plane_z0,10.)
        for record in records:
            self.assertEqual(record[0x14:0x18],bytes(4))
            self.assertEqual(record[:0x14],bytes([0xa5])*0x14)
            self.assertEqual(record[0x18:],bytes([0xa5])*8)

    def test_rejects_zero_or_degenerate_depth_span(self):
        records=[bytearray(32) for _ in range(100)]
        with self.assertRaises(ValueError):
            configure_render_viewport(RenderViewport(0,0,1,1,0,1),records)
        with self.assertRaises(ValueError):
            configure_render_viewport(RenderViewport(0,0,1,1,1,1),records)

    def test_requires_the_original_scratch_table_shape(self):
        with self.assertRaises(ValueError):
            configure_render_viewport(RenderViewport(0,0,1,1,.1,1),[])

    def test_viewport_bounds_feed_the_clip_code_helper_as_float_words(self):
        records=[bytearray(32) for _ in range(100)]
        state=configure_render_viewport(
            RenderViewport(0.,0.,640.,480.,10.,.0016666667),records)
        self.assertEqual(classify_render_position((10.,20.,.5,10.),state),0)
        self.assertNotEqual(classify_render_position((-1.,20.,.5,10.),state),0)

    def test_alternate_render_bounds_preserve_native_global_aliases(self):
        state=set_alternate_render_bounds(10.,20.,650.,500.)
        globals_by_address=state.globals_by_address()
        self.assertEqual(globals_by_address[0x00993848],10.)
        self.assertEqual(globals_by_address[0x009938b0],650.)
        self.assertEqual(globals_by_address[0x009938ac],20.)
        self.assertEqual(globals_by_address[0x00993bb0],500.)
        self.assertEqual(globals_by_address[0x0099248c],10.)
        self.assertEqual(globals_by_address[0x00993840],650.)
        self.assertEqual(globals_by_address[0x00993a48],20.)
        self.assertEqual(globals_by_address[0x00993bb4],500.)

    def test_six_word_alternate_viewport_preserves_all_alias_bits(self):
        values=(0x00000000,0x80000000,0x7fc12345,0xff800000,
                0x00000001,0xffffffff)
        state=set_alternate_render_viewport_words(*values)
        self.assertEqual(tuple(state.values()),
                         (values[0],values[2],values[1],values[3],values[5],
                          values[4],values[0],values[2],values[1],values[3],
                          values[5],values[4]))
        with self.assertRaises(ValueError):
            set_alternate_render_viewport_words(*values[:-1])
        with self.assertRaises(ValueError):
            set_alternate_render_viewport_words(*values[:-1],-1)

    def test_surface_clamping_produces_callback_edges_and_clip_state(self):
        result=prepare_render_viewport_request(
            RenderViewportRequest(800,600,500,450,400,300))
        self.assertEqual(result.callback_args,(500,450,800,600))
        self.assertEqual((result.clamped_width,result.clamped_height),(300,150))
        self.assertEqual(result.globals_by_address[0x00b31fbc],500.)
        self.assertEqual(result.globals_by_address[0x008c672c],800.)
        self.assertEqual(result.globals_by_address[0x00993bb0],600.)

    def test_client_rect_and_alternate_path_are_explicit(self):
        request=RenderViewportRequest(800,600,100,80,500,400,
                                      alternate_path=True,
                                      client_width=300,client_height=200)
        result=prepare_render_viewport_request(request,query_client_rect=True)
        self.assertEqual(result.callback_args,(100,80,300,200))
        self.assertEqual((result.clamped_width,result.clamped_height),(500,400))
        self.assertIsNone(result.viewport_state)
        self.assertEqual(result.globals_by_address[0x00b424a8],300.)
        self.assertEqual(result.globals_by_address[0x00b424a0],200.)


if __name__ == '__main__':
    unittest.main()
