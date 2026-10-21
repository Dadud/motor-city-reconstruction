import unittest

from client.world_object_damping import WorldObjectMotion
from client.world_object_maintenance import WorldObjectMaintenance, maintain_world_object
from client.tire_response import f32


def identity(state):
    return state


def motion(angular_velocity=(1.0, 2.0, 3.0), linear_velocity=(4.0, 5.0, 6.0), counter=0):
    return WorldObjectMotion(counter, linear_velocity, angular_velocity)


class WorldObjectMaintenanceTests(unittest.TestCase):
    def test_inactive_owner_skips_child(self):
        state = WorldObjectMaintenance(motion(), False, 0, 10)
        self.assertIs(maintain_world_object(state, lambda _: self.fail('inactive child ran')), state)

    def test_damps_linear_and_angular_velocity_when_maintenance_value_is_lower(self):
        state = WorldObjectMaintenance(motion(), True, 0, 1)
        result = maintain_world_object(state, identity)
        factor = f32(0.99)
        self.assertEqual(result.motion.linear_velocity, tuple(f32(x * factor) for x in (4, 5, 6)))
        self.assertEqual(result.motion.angular_velocity, tuple(f32(x * factor) for x in (1, 2, 3)))

    def test_caps_angular_velocity_magnitude_at_ten(self):
        result = maintain_world_object(
            WorldObjectMaintenance(motion((12, 0, 0)), True, 1, 1), identity)
        self.assertEqual(result.motion.angular_velocity, (10.0, 0.0, 0.0))

    def test_angular_velocity_settling_nudge_requires_all_three_conditions(self):
        state = WorldObjectMaintenance(motion((0, 0, 0), counter=33), True, 0, 0)
        result = maintain_world_object(state, identity)
        self.assertEqual(result.motion.angular_velocity[0], f32(0.01))
        for changes in ({'motion': motion((0, 0, 0), counter=32)},
                        {'maintenance_value': 1},
                        {'motion': motion((0.02, 0, 0), counter=33)}):
            values = state.__dict__ | changes
            held = maintain_world_object(WorldObjectMaintenance(**values), identity)
            self.assertNotEqual(held.motion.angular_velocity[0], f32(0.01))

    def test_invokes_child_once_for_active_item(self):
        calls = []
        def child(state):
            calls.append(state)
            return WorldObjectMotion(state.contact_counter, state.linear_velocity, (2, 0, 0))
        state = WorldObjectMaintenance(motion(), True, 1, 1)
        maintain_world_object(state, child)
        self.assertEqual(calls, [state.motion])


if __name__ == '__main__':
    unittest.main()
