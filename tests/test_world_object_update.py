import unittest

from client.world_object_update import WorldObjectUpdate, update_world_object


def make_state(active=True):
    return WorldObjectUpdate(
        1, active, (2, -3, 1), (0.75, -0.25, 0.5), (0.25, -0.5, 0.125),
        (1, 0, 0, 0, 1, 0, 0, 0, 1),
        (0.03125, -0.015625, 0.0078125), (0.5, -0.25, 1),
        tuple(i / 8 for i in range(66)), (0.0,) * 66)


class WorldObjectUpdateTests(unittest.TestCase):
    def test_motion_and_transformed_geometry(self):
        result, projected = update_world_object(make_state(), object_phase=0)
        self.assertNotEqual(result.position, (2, -3, 1))
        self.assertNotEqual(result.rotation, (1, 0, 0, 0, 1, 0, 0, 0, 1))
        self.assertEqual(result.transposed_rotation[1], result.rotation[3])
        self.assertEqual(len(result.world_vertices), 66)
        self.assertNotEqual(result.world_vertices, (0.0,) * 66)
        self.assertEqual(projected, result.projected)

    def test_inactive_objects_do_not_dispatch(self):
        state = make_state(False)
        result = update_world_object(state, object_phase=0)
        self.assertIs(result, state)

    def test_periodic_repair_is_required_only_for_selected_id(self):
        state = make_state()
        repaired, _ = update_world_object(state, object_phase=2)
        self.assertEqual(len(repaired.rotation), 9)
        seen = []
        result, _ = update_world_object(state, object_phase=2,
                                        repair_matrix=lambda matrix, n: seen.append(n) or matrix)
        self.assertEqual(seen, [10])
        self.assertEqual(len(result.rotation), 9)


if __name__ == '__main__':
    unittest.main()
