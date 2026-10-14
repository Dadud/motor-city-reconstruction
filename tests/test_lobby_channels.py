import unittest

from client.lobby_channels import (
    CHANNEL_ERROR_ALREADY_OPEN,
    CHANNEL_ERROR_NOT_CONNECTED,
    CHANNEL_ERROR_UDP_PORT_MISMATCH,
    CHANNEL_PROTOCOL_TCP_A,
    CHANNEL_PROTOCOL_UDP_A,
    ChannelAddRequest,
    GAME_NETWORK_TASK_CHANNEL_ADD,
    normalize_task_result,
    uses_udp,
)


class LobbyChannelTests(unittest.TestCase):
    def test_udp_protocol_detection(self):
        self.assertTrue(uses_udp(CHANNEL_PROTOCOL_UDP_A))
        self.assertFalse(uses_udp(CHANNEL_PROTOCOL_TCP_A))

    def test_not_connected_rejected(self):
        request = ChannelAddRequest(CHANNEL_PROTOCOL_TCP_A, 0, 0, False)
        self.assertEqual(request.validate(), CHANNEL_ERROR_NOT_CONNECTED)

    def test_existing_channel_rejected(self):
        request = ChannelAddRequest(CHANNEL_PROTOCOL_TCP_A, 9, 0, True, existing_channel_id=9)
        self.assertEqual(request.validate(), CHANNEL_ERROR_ALREADY_OPEN)

    def test_zero_channel_id_and_unrelated_channel_do_not_collide(self):
        for requested in (0, 10):
            request = ChannelAddRequest(CHANNEL_PROTOCOL_TCP_A, requested, 0, True, existing_channel_id=9)
            self.assertIsNone(request.validate())

    def test_udp_port_mismatch_rejected(self):
        request = ChannelAddRequest(
            CHANNEL_PROTOCOL_UDP_A, 0, 7000, True, existing_udp_port=43300)
        self.assertEqual(request.validate(), CHANNEL_ERROR_UDP_PORT_MISMATCH)

    def test_task_seven_normalizes_success_one_to_zero(self):
        self.assertEqual(normalize_task_result(GAME_NETWORK_TASK_CHANNEL_ADD, 1), 0)
        self.assertEqual(normalize_task_result(GAME_NETWORK_TASK_CHANNEL_ADD, -6), -6)


if __name__ == '__main__':
    unittest.main()
