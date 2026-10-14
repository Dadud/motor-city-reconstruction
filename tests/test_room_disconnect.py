import random
import struct
import unittest

from client.room_disconnect import PendingRoomOperation, prepare_room_disconnect
from client.room_join_request import RoomJoinInputs


class RoomDisconnectTests(unittest.TestCase):
    def image(self, connected, pending=0):
        image = bytearray(random.Random(0x44d750).randbytes(0x3c0))
        struct.pack_into('<H', image, 0xec, connected)
        struct.pack_into('<I', image, 0x3a8, pending)
        struct.pack_into('<I', image, 0x39c, 7)
        struct.pack_into('<I', image, 0xc0, 99)
        return bytes(image)

    def test_disconnected_resets_without_task_even_when_pending(self):
        image = self.image(0, 5)
        for wait in (False, True):
            outcome = prepare_room_disconnect(image, wait_for_completion=wait)
            self.assertIsNone(outcome.argument)
            self.assertIsNone(outcome.task_kind)
            self.assertEqual(outcome.immediate_return, 0)
            self.assertFalse(outcome.tracked)
            self.assertEqual(outcome.room_image[0x3a8:0x3ac], image[0x3a8:0x3ac])

    def test_connected_retains_old_ids_in_request_and_resets_local_inputs(self):
        image = self.image(0xffff)
        for wait in (False, True):
            outcome = prepare_room_disconnect(image, wait_for_completion=wait)
            self.assertEqual(outcome.argument, struct.pack('<II', 7, 99))
            self.assertEqual(outcome.task_kind, 1)
            self.assertEqual(outcome.tracked, wait)
            self.assertEqual(outcome.immediate_return, None if wait else 0)
            inputs = RoomJoinInputs.from_room_image(outcome.room_image)
            self.assertEqual((inputs.server_selector, inputs.protocol, inputs.channel_id,
                              inputs.name, inputs.max_ready), (7, 0x21, 0, b'', 0))
            self.assertEqual(inputs.opaque_data, bytes(256))
            self.assertEqual(outcome.room_image[0x1fa:], image[0x1fa:])
            for offset in (0xe5, 0xee, 0xef):
                self.assertEqual(outcome.room_image[offset], image[offset])
            self.assertEqual(outcome.reset_owner_offsets, (0x2e0, 0x1fc))

    def test_pending_connected_requires_observed_completion(self):
        with self.assertRaises(PendingRoomOperation):
            prepare_room_disconnect(self.image(1, 1), wait_for_completion=True)

    def test_invalid_input(self):
        for image in (bytes(0x3ab), bytes(65537), bytearray(0x3c0)):
            with self.assertRaises(ValueError):
                prepare_room_disconnect(image, wait_for_completion=False)
        with self.assertRaises(ValueError):
            prepare_room_disconnect(self.image(0), wait_for_completion=1)
