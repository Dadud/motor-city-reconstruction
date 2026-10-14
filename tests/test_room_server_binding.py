import random
import struct
import unittest

from client.room_join_request import RoomJoinInputs
from client.room_server_binding import NETWORK_OWNER_MIN_SIZE, apply_server_connection_result


class RoomServerBindingTests(unittest.TestCase):
    def test_success_binds_embedded_room_to_returned_connection(self):
        original = bytearray(random.Random(0x454d50).randbytes(NETWORK_OWNER_MIN_SIZE + 19))
        original[0x140:0x160] = bytes(32)
        for result in (0, 7, 44, 0x7fffffff):
            outcome = apply_server_connection_result(bytes(original), result)
            expected = bytearray(original)
            for offset, value in ((0x5cc, result), (0x43c, result), (0x5fc, 1), (0x600, 0)):
                struct.pack_into('<I', expected, offset, value)
            self.assertEqual(outcome.owner_image, bytes(expected))
            room = RoomJoinInputs.from_room_image(outcome.owner_image[0xa0:0x458])
            self.assertEqual(room.server_selector, result)
            self.assertEqual(outcome.notification, (result, 0))
            self.assertTrue(outcome.mini_room_list_requested)

    def test_failure_preserves_previous_selector_and_connected_flag(self):
        original = bytes([0xa5]) * NETWORK_OWNER_MIN_SIZE
        for result in (-1, -6, -51, -0x80000000):
            outcome = apply_server_connection_result(original, result)
            expected = bytearray(original)
            struct.pack_into('<i', expected, 0x5cc, result)
            struct.pack_into('<i', expected, 0x5f4, result)
            struct.pack_into('<I', expected, 0x600, 0)
            self.assertEqual(outcome.owner_image, bytes(expected))
            self.assertIsNone(outcome.notification)
            self.assertFalse(outcome.mini_room_list_requested)

    def test_rejects_invalid_image_and_native_result(self):
        for image in (bytes(NETWORK_OWNER_MIN_SIZE - 1), bytearray(NETWORK_OWNER_MIN_SIZE)):
            with self.assertRaises(ValueError):
                apply_server_connection_result(image, 0)
        for result in (True, 0x80000000, -0x80000001, 0.0):
            with self.assertRaises(ValueError):
                apply_server_connection_result(bytes(NETWORK_OWNER_MIN_SIZE), result)
