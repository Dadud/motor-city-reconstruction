import unittest

from client.track_surface import average_surface_vertex_color


class TrackSurfaceColorTests(unittest.TestCase):
    def test_missing_surface_is_opaque_gray(self):
        self.assertEqual(average_surface_vertex_color(0, None, (), ()),
                         0xff7f7f7f)

    def test_averages_each_packed_channel_independently(self):
        colors = (0xff000000, 0xff04080c, 0xff081018, 0xff0c1824)
        self.assertEqual(average_surface_vertex_color(
            7, (0, 0, 0, 0), colors, ((0, 1, 2, 3),)),
            0xff060c12)

    def test_quad_vertex_order_does_not_change_average(self):
        colors = (0xff010203, 0xff111213, 0xff212223, 0xff313233)
        a = average_surface_vertex_color(0, (0, 0, 0, 0), colors,
                                         ((0, 1, 2, 3),))
        b = average_surface_vertex_color(0, (0, 0, 0, 0), colors,
                                         ((3, 1, 0, 2),))
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
