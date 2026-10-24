import unittest
import struct

from client.render_segment_clip import SegmentClipBounds, clip_render_segment


class RenderSegmentClipTests(unittest.TestCase):
    def setUp(self):
        self.bounds=SegmentClipBounds(.1,1.,-1.,1.,-1.,1.,0xcf)

    def test_passes_through_when_both_codes_are_zero(self):
        first=(0.,0.,.2,.2,.3,.4)
        second=(.5,.5,.8,.8,.7,.6)
        as_float32=lambda values: struct.unpack('<6f',struct.pack('<6f',*values))
        self.assertEqual(clip_render_segment(first,second,0,0,self.bounds),
                         (as_float32(first),as_float32(second)))

    def test_rejects_shared_outside_plane(self):
        self.assertIsNone(clip_render_segment(
            (-2.,0.,.2,.5,.3,.4),(-3.,.2,.8,.7,.7,.6),0x10,0x10,
            self.bounds))

    def test_clips_endpoint_against_each_plane(self):
        first=(0.,0.,0.,.05,.3,.4)
        second=(0.,0.,1.,.5,.7,.6)
        near=clip_render_segment(first,second,1,0,self.bounds)
        self.assertIsNotNone(near)
        self.assertEqual(near[0][:4],(0.,0.,0.,self.bounds.near_w))
        far=clip_render_segment((0.,0.,1.,1.2,.3,.4),second,2,0,self.bounds)
        self.assertEqual(far[0][:4],(0.,0.,1.,self.bounds.far_w))
        left=clip_render_segment((-2.,0.,.2,.5,.3,.4),second,0x10,0,self.bounds)
        self.assertEqual(left[0][0],self.bounds.x_min)
        top=clip_render_segment((0.,2.,.2,.5,.3,.4),second,8,0,self.bounds)
        self.assertEqual(top[0][1],self.bounds.y_max)

    def test_validates_codes_and_vertices(self):
        with self.assertRaises(ValueError):
            clip_render_segment((0.,)*5,(0.,)*6,0,0,self.bounds)
        with self.assertRaises(ValueError):
            clip_render_segment((0.,)*6,(0.,)*6,256,0,self.bounds)


if __name__ == '__main__':
    unittest.main()
