import struct
import unittest

from client.render_polygon_clip import (
    clip_triangle_near_plane, clip_triangle_x_max_plane,
    clip_triangle_x_min_plane,
    clip_triangle_near_then_y_max,
    clip_triangle_near_then_y_min,clip_triangle_near_then_x_plane,
    clip_triangle_near_then_y_max_then_x_min,
    clip_triangle_y_max_plane,
    clip_triangle_y_min_plane, clip_triangle_planes,
    reject_triangle_on_shared_near_plane)


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def _float(word):
    return struct.unpack('<f',struct.pack('<I',word))[0]


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

    def test_ordered_multiplane_path_handles_all_supported_passes(self):
        # Input points 0 and 2 exercise lower-Y and near-W together; the
        # sequentially generated intersections then reach the left-X pass.
        vertices=(
            (_word(-2.),_word(-2.),_word(0.),_word(.05),
             0xff112233,0,_word(.2),_word(.4),0,0),
            (_word(2.),_word(0.),_word(0.),_word(.5),
             0xff445566,0,_word(.4),_word(.6),0,0),
            (_word(-3.),_word(2.),_word(0.),_word(.7),
             0xff778899,0,_word(.8),_word(.9),0,0),
        )
        count,output=clip_triangle_planes((0x15,0,0x30),vertices,
            plane_mask=0x15,plane_w=.1,y_min=-1.,y_max=1.,
            x_min=-1.,x_max=1.)
        self.assertGreaterEqual(count,1)
        self.assertEqual(count,len(output)-2)
        self.assertLessEqual(len(output),8)

    def test_exactly_one_near_plane_outcode_is_required(self):
        with self.assertRaises(ValueError):
            clip_triangle_near_plane((1,1,0),self.vertices,plane_w=.1)
        with self.assertRaises(ValueError):
            clip_triangle_near_plane((1,2,0),self.vertices,plane_w=.1)

    def test_near_then_upper_y_composes_four_vertex_intermediate(self):
        vertices=(
            (_word(2.),_word(4.),_word(0.),_word(.05),
             0xff112233,0,_word(.2),_word(.4),0,0),
            (_word(-2.),_word(0.),_word(0.),_word(.5),
             0xff445566,0,_word(.4),_word(.6),0,0),
            (_word(0.),_word(-2.),_word(0.),_word(.7),
             0xff778899,0,_word(.8),_word(.9),0,0),
        )
        count,clipped=clip_triangle_near_then_y_max(
            (9,0,0),vertices,plane_w=.1,y_max=1.)
        self.assertEqual(count,2)
        self.assertEqual(len(clipped),4)
        self.assertTrue(all(_float(vertex[1])<=1. for vertex in clipped))

    def test_near_then_lower_y_composes(self):
        count,clipped=clip_triangle_near_then_y_min(
            (5,0,0),self.vertices,plane_w=.1,y_min=-1.)
        self.assertGreaterEqual(count,1)
        self.assertTrue(all(_float(vertex[1])>=-1. for vertex in clipped))

    def test_near_then_x_planes_compose(self):
        for upper,boundary,codes in ((False,-1.,(0x11,0,0)),
                                     (True,1.,(0x21,0,0))):
            points=((-3.,0.,.05),(0.,0.,.5),(2.,0.,.75)) if not upper else (
                   (3.,0.,.05),(0.,0.,.5),(-2.,0.,.75))
            vertices=tuple((_word(x),_word(y),_word(.2),_word(w),
                self.vertices[i][4],0,_word(.1),_word(.2),0,0)
                for i,(x,y,w) in enumerate(points))
            count,clipped=clip_triangle_near_then_x_plane(
                codes,vertices,plane_w=.1,x_boundary=boundary,
                upper=upper)
            self.assertGreaterEqual(count,1)
            xs=[_float(vertex[0]) for vertex in clipped]
            self.assertTrue(all(x>=boundary-1e-6 for x in xs) if not upper
                            else all(x<=boundary+1e-6 for x in xs))

    def test_near_upper_y_left_x_three_plane_path(self):
        points=((-3.,3.,.05),(2.,0.,.5),(0.,-2.,.75))
        vertices=tuple((_word(x),_word(y),_word(.2),_word(w),
            self.vertices[i][4],0,_word(.1),_word(.2),0,0)
            for i,(x,y,w) in enumerate(points))
        count,clipped=clip_triangle_near_then_y_max_then_x_min(
            (0x19,0,0),vertices,plane_w=.1,y_max=1.,x_min=-1.)
        self.assertGreaterEqual(count,1)
        self.assertTrue(all(_float(vertex[1])<=1. for vertex in clipped))
        self.assertTrue(all(_float(vertex[0])>=-1. for vertex in clipped))

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
