import unittest

from client.race_entry import build_race_entry_plan, probe_race_entry_path
from client.game_network import GameNetworkTask
from client.lobby_channels import (
    CHANNEL_PROTOCOL_TCP_A,
    CHANNEL_PROTOCOL_UDP_A,
    GAME_NETWORK_TASK_CHANNEL_ADD,
    GAME_NETWORK_TASK_GAME_START,
    GAME_NETWORK_TASK_MINI_ROOM_LIST,
    GAME_NETWORK_TASK_SERVER_CONNECT,
)
from client.server_discovery import PatchNetworkSettings


class RaceEntryTests(unittest.TestCase):
    def test_retains_explicit_tasks_and_protocol_independent_of_fast_join(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        tasks = (GameNetworkTask(8, b'caller-args'), GameNetworkTask(7, b'other-args'))
        plan = build_race_entry_plan(settings, tasks=tasks, channel_protocol=CHANNEL_PROTOCOL_UDP_A)
        self.assertEqual(plan.channel_protocol, CHANNEL_PROTOCOL_UDP_A)
        self.assertEqual(plan.task_kinds, (8, 7))
        self.assertIs(plan.tasks, tasks)

    def test_requires_explicit_choices(self):
        with self.assertRaises(TypeError):
            build_race_entry_plan(None)

    def test_probe_reports_patch_settings(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        probe = probe_race_entry_path(settings)
        self.assertFalse(probe['race_entry_probe_passed'])
        self.assertTrue(probe['configured_fast_join'])
        self.assertIsNone(probe['fast_join_tcp_preferred'])
        self.assertIsNone(probe['channel_protocol'])
        self.assertEqual(probe['positional_updates_hz'], 32)
        self.assertIsNone(probe['update_interval_seconds'])
        self.assertTrue(probe['missing_task_order'])
        self.assertTrue(probe['missing_authenticated_arguments'])
        self.assertFalse(probe['room_channel_probe_passed'])
        self.assertEqual(probe['recovered_task_kinds'], [])

    def test_missing_fast_join_preserved_as_unknown(self):
        plan = build_race_entry_plan(PatchNetworkSettings(None, None, None, None),
                                     tasks=(), channel_protocol=CHANNEL_PROTOCOL_TCP_A)
        self.assertIsNone(plan.configured_fast_join)

    def test_not_connected_channel_add_rejected(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        with self.assertRaises(ValueError):
            build_race_entry_plan(settings, tasks=(), channel_protocol=CHANNEL_PROTOCOL_TCP_A,
                                  server_connected=False)


if __name__ == '__main__':
    unittest.main()
