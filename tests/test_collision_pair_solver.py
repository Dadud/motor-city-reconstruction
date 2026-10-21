import unittest

from client.collision_pair_geometry import OrientedCollisionBox
from client.collision_pair_solver import CollisionPairBody, resolve_collision_pair


def body(center, *, mass=1000, mode=0, gate=0, peer_gate=1):
    box = OrientedCollisionBox(center, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (1, 1, 1))
    return CollisionPairBody(box, mass, mode, gate, peer_gate)


class CollisionPairSolverTests(unittest.TestCase):
    def test_overlapping_pair_uses_the_32_step_limit(self):
        result = resolve_collision_pair(body((0, 0, 0)), body((1, 0, 0)))
        self.assertTrue(result.collided)
        self.assertEqual(result.correction_steps, 32)
        self.assertEqual(result.owner.box.center, (-0.5, 0.0, 0.0))
        self.assertEqual(result.target.box.center, (1.5, 0.0, 0.0))

    def test_solver_stops_after_the_sampled_boxes_separate(self):
        result = resolve_collision_pair(body((0, 0, 0)), body((1.5, 0, 0)))
        self.assertTrue(result.collided)
        self.assertEqual(result.correction_steps, 17)
        self.assertEqual(result.owner.box.center, (-0.265625, 0.0, 0.0))
        self.assertEqual(result.target.box.center, (1.765625, 0.0, 0.0))

    def test_separated_pair_is_unchanged(self):
        result = resolve_collision_pair(body((0, 0, 0)), body((3, 0, 0)))
        self.assertFalse(result.collided)
        self.assertEqual(result.correction_steps, 0)
        self.assertEqual(result.owner.box.center, (0, 0, 0))
        self.assertEqual(result.target.box.center, (3, 0, 0))


if __name__ == '__main__':
    unittest.main()
