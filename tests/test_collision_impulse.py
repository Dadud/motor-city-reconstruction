import unittest
from client.collision_impulse import CollisionInertia, impulse_motion, plane_height

IDENTITY=(1,0,0,0,1,0,0,0,1)


class CollisionImpulseTests(unittest.TestCase):
    def setUp(self): self.body=CollisionInertia(0.5,(1,2,3),IDENTITY,IDENTITY)

    def test_central_inward_impulse_changes_only_translation(self):
        result=impulse_motion(self.body,(0,-2,0),(0,0,0),(0,1,0))
        self.assertEqual(result.linear,(0,-1,0))
        self.assertEqual(result.angular,(0,0,0))

    def test_translation_gate_does_not_gate_angular_response(self):
        result=impulse_motion(self.body,(0,2,0),(1,0,0),(0,1,0))
        self.assertEqual(result.linear,(0,0,0))
        self.assertEqual(result.angular,(0,0,6))

    def test_body_frame_rotates_anisotropic_inertia(self):
        body=CollisionInertia(0.5,(1,2,3),(0,0,1,0,1,0,-1,0,0),(0,0,-1,0,1,0,1,0,0))
        result=impulse_motion(body,(0,2,0),(1,0,0),(0,1,0))
        self.assertEqual(result.angular,(0,0,2))

    def test_height_ignores_query_height(self):
        self.assertEqual(plane_height((1,2,3),(1,10,2),(3,-999,4)),6)
        self.assertEqual(plane_height((1,2,3),(1,10,2),(3,999,4)),6)

    def test_vertical_plane_and_invalid_inertia_rejected(self):
        with self.assertRaises(ValueError):plane_height((1,0,0),(0,0,0),(0,0,0))
        bad=CollisionInertia(float('nan'),(1,2,3),IDENTITY,IDENTITY)
        with self.assertRaises(ValueError):impulse_motion(bad,(0,0,0),(0,0,0),(0,1,0))


if __name__=='__main__':unittest.main()
