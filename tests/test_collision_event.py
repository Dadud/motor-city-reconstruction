import struct
import unittest

from client.collision_event import (HANDLER_COUNT,
                                    apply_collision_contact_event,
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


if __name__ == '__main__':
    unittest.main()
