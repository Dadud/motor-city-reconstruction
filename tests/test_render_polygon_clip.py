import struct
import unittest

from client.render_polygon_clip import (
    clip_triangle_near_plane, clip_triangle_x_max_plane,
    clip_triangle_x_min_plane,
    clip_triangle_y_max_plane,
    clip_triangle_y_min_plane, reject_triangle_on_shared_near_plane)


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


class RenderPolygonClipTests(unittest.TestCase):
    def setUp(self):
        self.vertices=(
            (_word(-2.),_word(0.),_word(.2),_word(.05),
             0xff0000ff,0,_word(.1),_word(.2),0,0),
            (_word(2.),_word(0.),_word(.2),_word(.5),
             0xff00ff00,0,_word(.8),_word(.2),0,0),
            (_word(0.),_word(3.),_word(.2),_word(.75),
             0xffff0000,0,_word(.4),_word(.9),0,0),
        )

    def test_near_plane_crossing_emits_four_callback_vertices(self):
        count,vertices=clip_triangle_near_plane(
            (1,0,0),self.vertices,plane_w=.1)
        self.assertEqual(count,2)
        self.assertEqual(len(vertices),4)
        self.assertEqual(vertices[0][4],0xffff0000)
        self.assertEqual(vertices[1][3],_word(.1))
        self.assertEqual(vertices[2][3],_word(.1))
        self.assertEqual(vertices[3][4],0xff00ff00)

    def test_exactly_one_near_plane_outcode_is_required(self):
        with self.assertRaises(ValueError):
            clip_triangle_near_plane((1,1,0),self.vertices,plane_w=.1)
        with self.assertRaises(ValueError):
            clip_triangle_near_plane((1,2,0),self.vertices,plane_w=.1)

    def test_shared_near_plane_rejection_remains_available(self):
        self.assertEqual(reject_triangle_on_shared_near_plane(
            (1,0x11,0x21)),0xffffffff)

    def test_upper_y_plane_clips_one_outside_vertex(self):
        vertices=(
            (_word(-2.),_word(0.),_word(.2),_word(.5),
             0xff0000ff,0,_word(.1),_word(.2),0,0),
            (_word(2.),_word(3.),_word(.2),_word(.6),
             0xff00ff00,0,_word(.8),_word(.2),0,0),
            (_word(0.),_word(-1.),_word(.2),_word(.75),
             0xffff0000,0,_word(.4),_word(.9),0,0),
        )
        count,clipped=clip_triangle_y_max_plane(
            (0,8,0),vertices,y_max=1.)
        self.assertEqual(count,2)
        self.assertEqual(len(clipped),4)
        self.assertTrue(all(vertex[1]==_word(1.)
                            for vertex in clipped[2:4]))

    def test_lower_y_plane_clips_one_outside_vertex(self):
        vertices=(
            (_word(-2.),_word(-3.),_word(.2),_word(.5),
             0xff0000ff,0,_word(.1),_word(.2),0,0),
            (_word(2.),_word(0.),_word(.2),_word(.6),
             0xff00ff00,0,_word(.8),_word(.2),0,0),
            (_word(0.),_word(2.),_word(.2),_word(.75),
             0xffff0000,0,_word(.4),_word(.9),0,0),
        )
        count,clipped=clip_triangle_y_min_plane(
            (4,0,0),vertices,y_min=-1.)
        self.assertEqual(count,2)
        self.assertTrue(all(vertex[1]==_word(-1.)
                            for vertex in clipped[1:3]))

    def test_left_x_plane_clips_one_outside_vertex(self):
        vertices=(
            (_word(-3.),_word(-2.),_word(.2),_word(.5),
             0xff0000ff,0,_word(.1),_word(.2),0,0),
            (_word(0.),_word(2.),_word(.2),_word(.6),
             0xff00ff00,0,_word(.8),_word(.2),0,0),
            (_word(2.),_word(0.),_word(.2),_word(.75),
             0xffff0000,0,_word(.4),_word(.9),0,0),
        )
        count,clipped=clip_triangle_x_min_plane(
            (0x10,0,0),vertices,x_min=-1.)
        self.assertEqual(count,2)
        self.assertTrue(all(vertex[0]==_word(-1.)
                            for vertex in clipped[1:3]))

    def test_right_x_plane_clips_one_outside_vertex(self):
        vertices=(
            (_word(3.),_word(-2.),_word(.2),_word(.5),
             0xff0000ff,0,_word(.1),_word(.2),0,0),
            (_word(0.),_word(2.),_word(.2),_word(.6),
             0xff00ff00,0,_word(.8),_word(.2),0,0),
            (_word(-2.),_word(0.),_word(.2),_word(.75),
             0xffff0000,0,_word(.4),_word(.9),0,0),
        )
        count,clipped=clip_triangle_x_max_plane(
            (0x20,0,0),vertices,x_max=1.)
        self.assertEqual(count,2)
        self.assertTrue(all(vertex[0]==_word(1.)
                            for vertex in clipped[1:3]))


if __name__=='__main__':
    unittest.main()
