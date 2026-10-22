import struct
import unittest

from client.collision_event import (HANDLER_COUNT,
                                    apply_collision_contact_event,
                                    apply_sampled_world_event_callback,
                                    lookup_collision_event_handler)


class CollisionEventTests(unittest.TestCase):
    def test_indexed_lookup_is_signed_and_bounded(self):
        image = bytearray(0x468)
        handlers = tuple(range(0x100, 0x100 + HANDLER_COUNT))
        for index, expected in ((-1, 0), (0, 0x100), (11, 0x10b), (12, 0)):
            struct.pack_into('<i', image, 0x464, index)
            self.assertEqual(lookup_collision_event_handler(image, handlers),
                             expected)

    def test_impact_sets_contact_state_deadline_and_flag(self):
        image = bytearray(0x1060)
        struct.pack_into('<I', image, 0x474, 2)
        struct.pack_into('<9f', image, 0x78, 1., 0., 0., 0., 1., 0.,
                         0., 0., 1.)
        struct.pack_into('<f', image, 0x3c8, 1.)
        struct.pack_into('<3f', image, 0x3cc, 0., 0., -1.)
        struct.pack_into('<f', image, 0x105c, 0.)

        result = apply_collision_contact_event(image, 1234)

        self.assertEqual(struct.unpack_from('<I', result, 0xe00)[0], 1)
        self.assertEqual(struct.unpack_from('<I', result, 0xe04)[0], 1534)
        self.assertEqual(struct.unpack_from('<I', result, 0xdf4)[0], 0x40)

    def test_receding_contact_clears_active_contact_flag(self):
        image = bytearray(0x1060)
        struct.pack_into('<I', image, 0x474, 2)
        struct.pack_into('<9f', image, 0x78, 1., 0., 0., 0., 1., 0.,
                         0., 0., 1.)
        struct.pack_into('<f', image, 0x3c8, 1.)
        struct.pack_into('<3f', image, 0x3cc, 0., 0., 1.)
        struct.pack_into('<I', image, 0xe00, 1)
        struct.pack_into('<I', image, 0xdf4, 0x45)

        result = apply_collision_contact_event(image)

        self.assertEqual(struct.unpack_from('<I', result, 0xe00)[0], 0)
        self.assertEqual(struct.unpack_from('<I', result, 0xdf4)[0], 0x5)

    def test_method_gates_preserve_the_body(self):
        image = bytearray(0x1060)
        self.assertEqual(apply_collision_contact_event(image), bytes(image))
        struct.pack_into('<I', image, 0x474, 2)
        self.assertEqual(apply_collision_contact_event(image), bytes(image))

    def test_sampled_callback_queues_data_and_counts_dispatch(self):
        image = bytearray(0x1100)
        handler = bytearray(0x40)
        struct.pack_into('<f', image, 0x3c8, 2.)
        struct.pack_into('<f', image, 0x105c, 3.)
        struct.pack_into('<I', image, 0x370, 0x71001234)
        struct.pack_into('<I', image, 0xe14, 4)
        struct.pack_into('<I', handler, 0x28, 7)

        body_result, handler_result, queued = apply_sampled_world_event_callback(
            image, handler, (.25, 1., -.5, 512.), 1000)

        self.assertTrue(queued)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xe00)[0], 1)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xe04)[0], 1300)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xe14)[0], 0x84)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xe80)[0],
                         0x71001234)
        self.assertEqual(struct.unpack_from('<4f', body_result, 0xe84),
                         (.25, 1., -.5, 512.))
        self.assertEqual(struct.unpack_from('<I', handler_result, 0x28)[0], 8)

    def test_sampled_callback_releases_existing_state_without_queueing(self):
        image = bytearray(0x1100)
        handler = bytearray(0x40)
        struct.pack_into('<f', image, 0x3c8, 2.)
        struct.pack_into('<f', image, 0x105c, 3.)
        struct.pack_into('<I', image, 0xe00, 1)
        struct.pack_into('<I', image, 0xdf4, 0x45)
        struct.pack_into('<I', handler, 0x28, 7)

        body_result, handler_result, queued = apply_sampled_world_event_callback(
            image, handler, (1., 2., 3., 4.), 1000)

        self.assertFalse(queued)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xe00)[0], 0)
        self.assertEqual(struct.unpack_from('<I', body_result, 0xdf4)[0], 5)
        self.assertEqual(struct.unpack_from('<I', handler_result, 0x28)[0], 7)

    def test_sampled_callback_strict_gates_preserve_both_objects(self):
        image = bytearray(0x1100)
        handler = bytes(0x40)
        struct.pack_into('<f', image, 0x3c8, 2.)
        struct.pack_into('<f', image, 0x105c, 11.17575)
        body_result, handler_result, queued = apply_sampled_world_event_callback(
            image, handler, (1., 2., 3., 4.), 1000)
        self.assertFalse(queued)
        self.assertEqual(body_result, bytes(image))
        self.assertEqual(handler_result, handler)


if __name__ == '__main__':
    unittest.main()
