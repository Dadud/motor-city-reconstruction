import unittest

from client.lobby_channels import CHANNEL_PROTOCOL_TCP_A
from client.lobby_room import RoomCallbacks, build_room_channel_plan, probe_room_channel_path
from client.server_discovery import PatchNetworkSettings


class LobbyRoomTests(unittest.TestCase):
    def test_fast_join_builds_tcp_room_plan(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        plan = build_room_channel_plan(settings)
        self.assertEqual(plan.channel_protocol, CHANNEL_PROTOCOL_TCP_A)
        self.assertEqual(plan.race_entry_task_kinds, (0, 5, 7, 8))

    def test_probe_reports_task_kinds(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        probe = probe_room_channel_path(settings)
        self.assertTrue(probe['room_channel_probe_passed'])
        self.assertTrue(probe['expects_channel_add'])
        self.assertTrue(probe['expects_game_start'])

    def test_invalid_callback_rejected(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        callbacks = RoomCallbacks(primary=object())
        with self.assertRaises(TypeError):
            build_room_channel_plan(settings, callbacks=callbacks)


if __name__ == '__main__':
    unittest.main()

