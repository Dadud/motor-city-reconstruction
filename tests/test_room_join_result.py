import random
import struct
import unittest

from client.room_join_result import (ROOM_WORKER_MIN_SIZE, apply_room_join_result,
                                    room_join_call, RoomJoinNotification)


class RoomJoinResultTests(unittest.TestCase):
    def test_nonnegative_result_preserves_previous_error_and_unrelated_fields(self):
        original = random.Random(0x44eba0).randbytes(ROOM_WORKER_MIN_SIZE + 32)
        for result in (0, 1, 0x7fffffff):
            transition = apply_room_join_result(original, result)
            expected = bytearray(original)
            struct.pack_into('<I', expected, 0xc0, result)
            struct.pack_into('<H', expected, 0xec, 1)
            struct.pack_into('<I', expected, 0x3a8, 0)
            self.assertEqual(transition.worker_image, bytes(expected))
            self.assertEqual(transition.return_code, 0)
            self.assertEqual(transition.notification, RoomJoinNotification(
                0x1fc, struct.unpack_from('<I', original, 0x39c)[0], result))

    def test_negative_result_preserves_channel_and_ready_flag(self):
        original = bytes([0xa5]) * ROOM_WORKER_MIN_SIZE
        for result in (-1, -6, -51, -0x80000000):
            transition = apply_room_join_result(original, result)
            expected = bytearray(original)
            struct.pack_into('<i', expected, 0x3a4, result)
            struct.pack_into('<I', expected, 0x3a8, 0)
            self.assertEqual(transition.worker_image, bytes(expected))
            self.assertEqual(transition.return_code, result)
            self.assertIsNone(transition.notification)

    def test_call_retains_opaque_values_and_exact_argument(self):
        original = bytearray(ROOM_WORKER_MIN_SIZE)
        struct.pack_into('<3I', original, 0x3ac, 0xffffffff, 1, 0x12345678)
        argument = bytes([0x5a]) * 0x15c
        call = room_join_call(bytes(original), argument)
        self.assertEqual((call.interface_token, call.caller_value_1, call.caller_value_2),
                         (0x12345678, 0xffffffff, 1))
        self.assertIs(call.argument, argument)

    def test_rejects_incomplete_images_and_non_int32_results(self):
        for image in (bytes(ROOM_WORKER_MIN_SIZE - 1), bytearray(ROOM_WORKER_MIN_SIZE)):
            with self.assertRaises(ValueError):
                apply_room_join_result(image, 0)
        for result in (True, 0x80000000, -0x80000001, 0.0):
            with self.assertRaises(ValueError):
                apply_room_join_result(bytes(ROOM_WORKER_MIN_SIZE), result)
        with self.assertRaises(ValueError):
            room_join_call(bytes(ROOM_WORKER_MIN_SIZE), bytes(0x15b))
