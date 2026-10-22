import struct
import unittest

from client.world_object_table_setup import prepare_world_object_table


class WorldObjectTableSetupTests(unittest.TestCase):
    def test_copies_descriptor_clears_workspace_initializes_and_replaces_pointer(self):
        count = 3
        base = 0x12000000
        objects = bytearray((i * 17 + 3) & 0xFF for i in range(count * 0x4F8))
        original = bytes(objects)
        rows = bytearray((i * 31 + 9) & 0xFF for i in range(count * 0x38))
        sources = {}
        expected_inputs = []
        for index in range(count):
            address = 0x71001000 + index * 0x200
            sources[address] = bytes((index * 7 + j * 13) & 0xFF for j in range(0xB0))
            struct.pack_into('<I', rows, index * 0x38 + 0x20, address)
            expected_inputs.append(sources[address][:0xA8])

        seen = []
        def initialize(record):
            seen.append(bytes(record[0x418:0x4C0]))
            record[0x20] = 0x5A

        prepare_world_object_table(objects, rows, sources,
                                   object_base_address=base,
                                   initialize_body=initialize)
        self.assertEqual(seen, expected_inputs)
        for index in range(count):
            offset = index * 0x4F8
            self.assertEqual(objects[offset + 0x418:offset + 0x4C0], expected_inputs[index])
            self.assertEqual(struct.unpack_from('<I', objects, offset + 0x4C0)[0], 0)
            self.assertEqual(objects[offset + 0x4C8:offset + 0x4EC], bytes(0x24))
            self.assertEqual(objects[offset + 0x20], 0x5A)
            self.assertEqual(struct.unpack_from('<I', rows, index * 0x38 + 0x20)[0],
                             base + offset)
            self.assertEqual(rows[index * 0x38:index * 0x38 + 0x20],
                             bytes((i * 31 + 9) & 0xFF
                                   for i in range(index * 0x38, index * 0x38 + 0x20)))
        self.assertNotEqual(bytes(objects), original)

    def test_missing_source_is_rejected_before_mutating_that_row(self):
        objects = bytearray(0x4F8)
        rows = bytearray(0x38)
        struct.pack_into('<I', rows, 0x20, 0x71000000)
        with self.assertRaises(ValueError):
            prepare_world_object_table(objects, rows, {},
                                       object_base_address=0x12000000,
                                       initialize_body=lambda _record: None)
        self.assertEqual(struct.unpack_from('<I', rows, 0x20)[0], 0x71000000)


if __name__ == '__main__':
    unittest.main()
