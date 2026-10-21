import unittest

from client.world_object_damping import WorldObjectMotion, update_world_object_motion
from client.tire_response import f32


class WorldObjectDampingTests(unittest.TestCase):
    def test_contact_branch_damps_angular_velocity_only(self):
        result = update_world_object_motion(WorldObjectMotion(1, (0.1, -0.2, 0.3), (1, -2, 3)))
        self.assertEqual(result.linear_velocity, tuple(map(f32, (0.1, -0.2, 0.3))))
        self.assertEqual(result.angular_velocity, tuple(f32(f32(value) * f32(0.9)) for value in (1.0, -2.0, 3.0)))

    def test_idle_branch_snaps_small_linear_velocity_and_preserves_large_angular_velocity(self):
        result = update_world_object_motion(WorldObjectMotion(0, (0.49, -0.5, 0.6), (0.2, 0.08, -0.1)))
        self.assertEqual(result.linear_velocity, tuple(map(f32, (0.0, -0.5, 0.6))))
        self.assertEqual(result.angular_velocity, tuple(map(f32, (0.2, 0.08, -0.1))))

    def test_each_angular_velocity_gate_clears_middle_component(self):
        for angles in ((0.049, 0.4, 0.4), (0.4, 0.049, 0.4), (0.4, 0.4, 0.049)):
            with self.subTest(angular_velocity=angles):
                result = update_world_object_motion(WorldObjectMotion(0, (1, 2, 3), angles))
                self.assertEqual(result.angular_velocity[1], 0.0)

    def test_velocity_thresholds_are_strict(self):
        result = update_world_object_motion(WorldObjectMotion(0, (0.5, 0, 0), (0.05, 0.05, 0.05)))
        self.assertEqual(result.linear_velocity[0], 0.5)
        self.assertEqual(result.angular_velocity, tuple(map(f32, (0.05, 0.05, 0.05))))


if __name__ == '__main__':
    unittest.main()
