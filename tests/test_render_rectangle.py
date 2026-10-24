import unittest

from client.render_rectangle import plan_rectangle_border_edges


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

    def test_input_words_are_range_checked(self):
        with self.assertRaises(ValueError):
            plan_rectangle_border_edges(0,0,1,1,0,(1,2,3,0x100000000))


if __name__=='__main__':
    unittest.main()
