import unittest

from client.mouse_mapping_snapshot import MouseMappingSource, publish_mouse_mapping_snapshot


class MouseMappingSnapshotTests(unittest.TestCase):
    def test_boolean_fields_are_normalized_and_mapping_globals_keep_their_destinations(self):
        record = bytearray(0x13)
        record[0x10:0x13] = bytes((0, 0x80, 2))
        result = publish_mouse_mapping_snapshot(MouseMappingSource(
            bytes(record), 0x11223344, 0x22334455, 0x33445566, 0x44556677))
        self.assertEqual((result.value_9e1654, result.value_9e1658,
                          result.value_9e165c), (0, 1, 1))
        self.assertEqual((result.value_9e1648, result.value_9e164c,
                          result.value_9e1668, result.value_9e1650),
                         (0x11223344, 0x22334455, 0x33445566, 0x44556677))

    def test_short_records_and_non_uint32_sources_are_rejected(self):
        with self.assertRaises(ValueError):
            publish_mouse_mapping_snapshot(MouseMappingSource(b'\0' * 0x12, 1, 2, 3, 4))
        with self.assertRaises(ValueError):
            publish_mouse_mapping_snapshot(MouseMappingSource(b'\0' * 0x13, -1, 2, 3, 4))


if __name__ == '__main__':
    unittest.main()
