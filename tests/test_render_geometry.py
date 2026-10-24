import struct
import unittest

from client.render_geometry import (RenderPolygonData,
                                    copy_render_rect_fields,
                                    extract_render_polygon_bounds)


class RenderGeometryTests(unittest.TestCase):
    def test_bounds_combine_vertices_with_header_x_extents(self):
        polygon=RenderPolygonData(
            ((4.,-3.,0.,0.,0.,0.,0.,0.),
             (7.,5.,0.,0.,0.,0.,0.,0.),
             (-2.,1.,0.,0.,0.,0.,0.,0.)),
            header_max_x=8.,header_min_x=2.)
        self.assertEqual(extract_render_polygon_bounds(polygon),
                         (-2.,-3.,10.,8.))

    def test_null_and_empty_polygon_default_to_zero_bounds(self):
        self.assertEqual(extract_render_polygon_bounds(None),(0.,0.,0.,0.))
        empty=RenderPolygonData((),0.,0.)
        self.assertEqual(extract_render_polygon_bounds(empty),(0.,0.,0.,0.))

    def test_optional_and_aliased_outputs_match_ordered_stores(self):
        polygon=RenderPolygonData(((1.,2.,0.,0.,0.,0.,0.,0.),),1.,1.)
        shared=bytearray(b'\xcd'*4)
        x_min=bytearray(b'\xcd'*4)
        values=extract_render_polygon_bounds(polygon,(x_min,None,shared,shared))
        self.assertEqual(struct.unpack('<f',x_min)[0],values[0])
        self.assertEqual(struct.unpack('<f',shared)[0],values[3])

    def test_invalid_record_shape_is_rejected(self):
        polygon=RenderPolygonData(((1.,2.),),1.,1.)
        with self.assertRaises(ValueError):
            extract_render_polygon_bounds(polygon)

    def test_rectangle_copy_writes_only_the_four_native_fields(self):
        memory=bytearray(range(64))
        original=bytes(memory)
        copy_render_rect_fields(memory,0,32)
        for offset in (4,8,12,16):
            self.assertEqual(memory[32+offset:36+offset],
                             original[offset:offset+4])
        self.assertEqual(memory[32:36],original[32:36])
        self.assertEqual(memory[52:64],original[52:64])

    def test_overlapping_rectangle_copy_uses_instruction_order(self):
        memory=bytearray(range(64))
        expected=bytearray(memory)
        for offset in (8,4):
            expected[4+offset:8+offset]=bytes(expected[8+offset:12+offset])
        saved_12=bytes(expected[20:24])
        word_16=bytes(expected[24:28])
        expected[20:24]=word_16
        expected[16:20]=saved_12
        copy_render_rect_fields(memory,8,4)
        self.assertEqual(memory,expected)


if __name__=='__main__':
    unittest.main()
