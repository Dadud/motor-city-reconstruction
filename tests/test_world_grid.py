import struct
import unittest

from client.world_grid import (HEADER_SIZE, PAYLOAD_OFFSET, SENTINEL,
                               fixup_world_grid)


def fixture():
    image = bytearray(PAYLOAD_OFFSET + 64)
    struct.pack_into('<4f', image, 0, -10., -20., 10., 20.)
    table = HEADER_SIZE
    payload = PAYLOAD_OFFSET
    # Direct sentinel leaf: two words of opaque data.
    struct.pack_into('<4I', image, table, SENTINEL, 2, 0, 0)
    # Normal top-level entry with one child, whose header is a sentinel leaf.
    struct.pack_into('<4I', image, table + 16, 1, 0, 0, 0)
    struct.pack_into('<4I', image, payload, 0x11, 0x22, 0x33, 0x44)
    struct.pack_into('<4I', image, payload + 8, 1, 0, 0, 0)
    struct.pack_into('<4I', image, payload + 24, SENTINEL, 2, 0, 0)
    struct.pack_into('<4I', image, payload + 40, 0xAA, 0xBB, 0xCC, 0xDD)
    return image


class WorldGridTests(unittest.TestCase):
    def test_relocates_sentinel_leaf_and_nested_four_way_nodes(self):
        image = fixture()
        original = bytes(image)
        base = 0x71000000
        result = fixup_world_grid(image, base)
        payload_base = base + PAYLOAD_OFFSET
        self.assertEqual(result.bounds, (-10., -20., 10., 20.))
        self.assertEqual((result.scale_x, result.scale_y), (3276.800048828125, 1638.4000244140625))
        self.assertEqual(struct.unpack_from('<4I', result.table, 0),
                         (SENTINEL, 2, payload_base, 0))
        self.assertEqual(struct.unpack_from('<4I', result.table, 16),
                         (payload_base + 8, 0, 0, 0))
        self.assertEqual(struct.unpack_from('<4I', result.payload, 8),
                         (payload_base + 24, 0, 0, 0))
        self.assertEqual(struct.unpack_from('<4I', result.payload, 24),
                         (SENTINEL, 2, payload_base + 40, 0))
        self.assertEqual(result.cursor_address, payload_base + 48)
        self.assertEqual(bytes(image), original)

    def test_zero_counts_leave_null_and_sentinel_pointer_slots_untouched(self):
        image = bytearray(PAYLOAD_OFFSET + 32)
        struct.pack_into('<4f', image, 0, 0., 0., 1., 1.)
        struct.pack_into('<4I', image, HEADER_SIZE,
                         SENTINEL, 0, 0x12345678, 0x87654321)
        result = fixup_world_grid(image, 0x71000000)
        self.assertEqual(result.table[:16], image[HEADER_SIZE:HEADER_SIZE + 16])
        self.assertEqual(result.cursor_address, 0x71000000 + PAYLOAD_OFFSET)

    def test_rejects_truncated_table_and_zero_extent(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            fixup_world_grid(bytes(PAYLOAD_OFFSET - 1), 0x71000000)
        image = bytearray(PAYLOAD_OFFSET)
        struct.pack_into('<4f', image, 0, 1., 0., 1., 2.)
        with self.assertRaisesRegex(ValueError, 'nonzero width'):
            fixup_world_grid(image, 0x71000000)


if __name__ == '__main__':
    unittest.main()
