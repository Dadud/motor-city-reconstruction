import unittest

from client.race_entry import build_race_entry_plan, probe_race_entry_path
from client.lobby_channels import (
    CHANNEL_PROTOCOL_TCP_A,
    GAME_NETWORK_TASK_CHANNEL_ADD,
    GAME_NETWORK_TASK_GAME_START,
    GAME_NETWORK_TASK_MINI_ROOM_LIST,
    GAME_NETWORK_TASK_SERVER_CONNECT,
)
from client.server_discovery import PatchNetworkSettings


class RaceEntryTests(unittest.TestCase):
    def test_fast_join_selects_tcp_channel_protocol(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        plan = build_race_entry_plan(settings)
        self.assertEqual(plan.channel_protocol, CHANNEL_PROTOCOL_TCP_A)
        self.assertEqual(plan.task_kinds, (
            GAME_NETWORK_TASK_SERVER_CONNECT,
            GAME_NETWORK_TASK_GAME_START,
            GAME_NETWORK_TASK_CHANNEL_ADD,
            GAME_NETWORK_TASK_MINI_ROOM_LIST,
        ))

    def test_probe_reports_patch_settings(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        probe = probe_race_entry_path(settings)
        self.assertTrue(probe['race_entry_probe_passed'])
        self.assertTrue(probe['fast_join_tcp_preferred'])
        self.assertEqual(probe['positional_updates_hz'], 32)
        self.assertAlmostEqual(probe['update_interval_seconds'], 1 / 32)
        self.assertTrue(probe['expects_game_start'])
        self.assertTrue(probe['room_channel_probe_passed'])

    def test_not_connected_channel_add_rejected(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        with self.assertRaises(ValueError):
            build_race_entry_plan(settings, server_connected=False)


if __name__ == '__main__':
    unittest.main()
