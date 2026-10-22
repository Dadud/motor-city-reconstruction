import unittest
from types import SimpleNamespace

from client.fce import Part
from client.track_object_animation import apply_track_object_pose


class TrackObjectPoseTests(unittest.TestCase):
    def test_pose_rotates_vertices_and_normals_then_applies_translation(self):
        part = Part('animated', (0, 0, 0), ((1, 2, 3),), ((1, 0, 0),), ())
        # Native matrix storage is column-major. This maps (x,y,z) to
        # (-y,x,z), a positive quarter turn around the vertical axis.
        pose = SimpleNamespace(rotation=(0, 1, 0, -1, 0, 0, 0, 0, 1),
                               translation=(10, 20, 30))
        posed = apply_track_object_pose(part, pose)
        self.assertEqual(posed.vertices, ((8, 21, 33),))
        self.assertEqual(posed.normals, ((0, 1, 0),))
        self.assertEqual(posed.origin, (0.0, 0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
