import unittest

from client.render_plane_math import plane_height


class RenderPlaneMathTests(unittest.TestCase):
    def test_solves_plane_height_at_point(self):
        self.assertEqual(plane_height((1.,2.,3.),(4.,5.,6.),(8.,0.,10.)),
                         -3.)

    def test_rejects_vertical_normal(self):
        with self.assertRaises(ValueError):
            plane_height((1.,0.,2.),(0.,0.,0.),(1.,0.,1.))


if __name__=='__main__':
    unittest.main()
