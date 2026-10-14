import struct
import unittest
from client.connection_disconnect import communication_socket_close_required, native_disconnect_result


class DisconnectTests(unittest.TestCase):
    def test_result_classification(self):
        self.assertEqual(native_disconnect_result(0), -20)
        for result in (1, 2, 0x80000000, 0xffffffff):
            self.assertEqual(native_disconnect_result(result), 0)
        for invalid in (-1, 0x100000000, True):
            with self.assertRaises(ValueError):
                native_disconnect_result(invalid)

    def test_close_requires_ownership_and_channel_guard(self):
        for flag194, channel, flag19c, expected in (
            (0, 0, 1, False), (1, 0, 0, True), (1, 7, 0, False),
            (1, 7, 1, True), (0xffffffff, 7, 0x80000000, True)):
            image = bytearray(0x1a0)
            for offset, value in ((8, channel), (0x194, flag194), (0x19c, flag19c)):
                struct.pack_into('<I', image, offset, value)
            self.assertEqual(communication_socket_close_required(bytes(image)), expected)
        with self.assertRaises(ValueError):
            communication_socket_close_required(bytes(0x19f))
