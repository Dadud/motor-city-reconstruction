import struct
import unittest

from client.world_dataset_layout import layout_pointer_record_section


class WorldDatasetLayoutTests(unittest.TestCase):
    def test_relocates_record_subarrays_and_odd_triangle_alignment(self):
        base = 0x71000000
        descriptor = base + 0x100
        table = base + 0x1000
        image = bytearray(0x3000)
        struct.pack_into('<II', image, descriptor - base, 1, 0)
        row = table - base
        struct.pack_into('<I', image, row + 0x1c, 3)
        struct.pack_into('<I', image, row + 0x24, 2)
        struct.pack_into('<I', image, row + 0x30, 1)
        result = layout_pointer_record_section(image, base, descriptor, table)
        self.assertEqual(struct.unpack_from('<I', image, descriptor - base + 4)[0], table)
        self.assertEqual(struct.unpack_from('<I', image, row + 0x20)[0], table + 0x38)
        self.assertEqual(struct.unpack_from('<I', image, row + 0x28)[0], table + 0x3b)
        self.assertEqual(struct.unpack_from('<I', image, row + 0x2c)[0], table + 0x53)
        self.assertEqual(struct.unpack_from('<I', image, row + 0x34)[0], table + 0x5b)
        self.assertEqual(result['cursor_address'], table + 0x7b)

    def test_empty_section_preserves_descriptor_and_cursor(self):
        base = 0x71000000
        image = bytearray(0x100)
        struct.pack_into('<II', image, 0x20, 0, 0xdeadbeef)
        before = bytes(image)
        result = layout_pointer_record_section(image, base, base + 0x20, base + 0x80)
        self.assertEqual(bytes(image), before)
        self.assertEqual(result['cursor_address'], base + 0x80)

    def test_zero_payload_pointer_is_null_and_even_triangle_count_is_unpadded(self):
        base = 0x71000000
        image = bytearray(0x2000)
        struct.pack_into('<II', image, 0, 1, 0)
        row = 0x100
        struct.pack_into('<I', image, row + 0x1c, 0)
        struct.pack_into('<I', image, row + 0x24, 1)
        struct.pack_into('<I', image, row + 0x30, 2)
        result = layout_pointer_record_section(image, base, base, base + row)
        self.assertEqual(struct.unpack_from('<I', image, row + 0x20)[0], 0)
        self.assertEqual(result['cursor_address'], base + row + 0x38 + 12 + 4 + 60)


if __name__ == '__main__':
    unittest.main()
