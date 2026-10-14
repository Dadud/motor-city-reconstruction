import unittest

from client.lobby_channels import CHANNEL_PROTOCOL_TCP_A, CHANNEL_PROTOCOL_UDP_B
from client.lobby_room import RoomCallerValues, build_room_channel_plan, probe_room_channel_path
from client.server_discovery import PatchNetworkSettings


class LobbyRoomTests(unittest.TestCase):
    def test_explicit_protocol_and_observed_opaque_caller_values(self):
        plan = build_room_channel_plan(channel_protocol=CHANNEL_PROTOCOL_UDP_B)
        self.assertEqual(plan.channel_protocol, CHANNEL_PROTOCOL_UDP_B)
        self.assertEqual(plan.caller_values, RoomCallerValues(-1, 1))

    def test_requires_explicit_protocol(self):
        with self.assertRaises(TypeError):
            build_room_channel_plan()

    def test_probe_reports_task_kinds(self):
        settings = PatchNetworkSettings(True, 2, 32, 'A' * 40)
        probe = probe_room_channel_path(settings)
        self.assertFalse(probe['room_channel_probe_passed'])
        self.assertIsNone(probe['channel_protocol'])
        self.assertEqual(probe['channel_add_task_kind'], 7)
        self.assertEqual(probe['channel_add_caller_values'], [-1, 1])
        self.assertTrue(probe['protocol_selection_unverified'])

    def test_caller_values_are_32_bit_data_not_python_functions(self):
        for value in (lambda: None, object(), True, -0x80000001, 0x100000000):
            with self.assertRaises(ValueError):
                build_room_channel_plan(channel_protocol=CHANNEL_PROTOCOL_TCP_A,
                                        caller_values=RoomCallerValues(primary=value))
        plan = build_room_channel_plan(channel_protocol=CHANNEL_PROTOCOL_TCP_A,
                                      caller_values=RoomCallerValues(primary=0xffffffff))
        self.assertEqual(plan.caller_values.primary, 0xffffffff)

    def test_existing_udp_state_rejects_conflicting_port(self):
        with self.assertRaisesRegex(ValueError, '-59'):
            build_room_channel_plan(channel_protocol=CHANNEL_PROTOCOL_UDP_B,
                                    requested_port=9000, existing_udp_port=9001)


if __name__ == '__main__':
    unittest.main()

