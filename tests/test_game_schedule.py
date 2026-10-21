import unittest

from client.game_schedule import build_game_task_lists


class GameTaskListTests(unittest.TestCase):
    def test_builds_both_original_lists_and_capacity_formulas(self):
        result = build_game_task_lists(
            vehicles=(0x1000, 0x2000), world_objects=(0x3000,),
            vehicle_flags=(3, 4), dynamic_service_payload=0x4000,
            capacity_source_count=2)

        self.assertEqual((result.primary_capacity, result.secondary_capacity), (25, 17))
        self.assertEqual(
            [(entry.priority, entry.callback, entry.payload) for entry in result.primary],
            [
                (6, 0x520c20, 0x1000), (6, 0x520c20, 0x2000),
                (6, 0x520c20, 0x3000), (6, 0x42d730, 0),
                (8, 0x43f550, 0), (10, 0x487790, 0x4000),
                (0x15, 0x469010, 0x1000), (0x15, 0x469010, 0x2000),
                (0x1e, 0x53c140, 0x1000), (0x1e, 0x53c140, 0x2000),
                (0x1e, 0x5779d0, 0x3000), (0x1e, 0x4265f0, 0),
                (0x1e, 0x426730, 0),
                (0x28, 0x45abe0, 0x1000), (0x28, 0x45abe0, 0x2000),
                (0x28, 0x4265b0, 0), (0x28, 0x45abe0, 0x3000),
                (0x32, 0x43d6e0, 0x1000), (0x32, 0x43d6e0, 0x2000),
                (0x32, 0x424ec0, 0), (0x32, 0x426770, 0),
                (100, 0x55f520, 0), (0x6e, 0x55d300, 0),
                (0x78, 0x5678f0, 0),
            ])
        self.assertEqual(
            [(entry.priority, entry.callback, entry.payload) for entry in result.secondary],
            [
                (6, 0x42d780, 0), (6, 0x459df0, 0),
                (0x19, 0x585790, 0x1000), (0x19, 0x585790, 0x2000),
                (0x1e, 0x520450, 0x1000), (0x1e, 0x520450, 0x2000),
                (0x1e, 0x520450, 0x3000), (0x23, 0x40adb0, 0),
                (100, 0x43f9d0, 0x1000), (100, 0x43f9d0, 0x2000),
                (100, 0x55f540, 0), (0x6e, 0x5850b0, 0),
            ])

    def test_conditional_secondary_vehicle_callback(self):
        result = build_game_task_lists(
            vehicles=(0x1000, 0x2000, 0x3000, 0x4000), world_objects=(),
            vehicle_flags=(1, 2, 3, 4), dynamic_service_payload=0,
            capacity_source_count=0)
        selected = [(entry.callback, entry.payload) for entry in result.secondary
                    if entry.callback == 0x585790]
        self.assertEqual(selected, [(0x585790, 0x3000), (0x585790, 0x4000)])

    def test_rejects_missing_or_malformed_observations(self):
        with self.assertRaisesRegex(ValueError, 'one observed flag word'):
            build_game_task_lists((0x1000,), (), (), 0, 0)
        with self.assertRaisesRegex(ValueError, 'non-null'):
            build_game_task_lists((0,), (), (0,), 0, 0)
        with self.assertRaisesRegex(ValueError, 'uint32'):
            build_game_task_lists((), (), (), -1, 0)
        with self.assertRaisesRegex(ValueError, 'overflows signed int32'):
            build_game_task_lists((), (), (), 0, 0x7fffffff)


if __name__ == '__main__':
    unittest.main()
