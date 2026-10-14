import struct
import unittest

from client.game_network import GameNetworkTask, race_entry_task_kinds
from client.lobby_channels import GAME_NETWORK_TASK_CHANNEL_ADD, GAME_NETWORK_TASK_GAME_START


class GameNetworkTests(unittest.TestCase):
    def test_round_trip_preserves_kind_and_argument(self):
        argument = b'room-args'
        task = GameNetworkTask(GAME_NETWORK_TASK_CHANNEL_ADD, argument)
        decoded = GameNetworkTask.decode(task.encode())
        self.assertEqual(decoded.kind, GAME_NETWORK_TASK_CHANNEL_ADD)
        self.assertEqual(decoded.argument, argument)

    def test_channel_add_normalizes_native_success_one(self):
        task = GameNetworkTask(GAME_NETWORK_TASK_CHANNEL_ADD, b'')
        self.assertEqual(task.normalized_result(1), 0)

    def test_race_entry_kinds_include_game_start_and_channel_add(self):
        kinds = race_entry_task_kinds()
        self.assertIn(GAME_NETWORK_TASK_GAME_START, kinds)
        self.assertIn(GAME_NETWORK_TASK_CHANNEL_ADD, kinds)

    def test_rejects_unknown_kind(self):
        payload = struct.pack('<I', 99) + bytes(8) + b'x'
        with self.assertRaises(ValueError):
            GameNetworkTask.decode(payload)


if __name__ == '__main__':
    unittest.main()
