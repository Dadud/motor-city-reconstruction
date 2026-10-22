import struct
import unittest

from client.collision_trigger_resources import (
    decode_collision_trigger_archive,
    load_collision_trigger_archives,
    normalize_collision_trigger_archive,
)


def archive(records, header=b'\x04\x04\x41\x00\x02\x00\x00\x00'):
    data = bytearray(header)
    for record in records:
        data.extend(record)
    struct.pack_into('<H', data, 4, len(records))
    return bytes(data)


class CollisionTriggerResourceTests(unittest.TestCase):
    @staticmethod
    def record(x=0, y=0, z=0, trailing=(0, 0)):
        return struct.pack('<5i', x, y, z, *trailing)

    def test_archive_reads_count_and_preserves_record_bytes(self):
        source = archive((self.record(100, -200, 300, (7, 9)),
                          self.record(1, 2, 3, (11, 13))))
        decoded = decode_collision_trigger_archive(source)
        self.assertEqual(decoded.header, source[:8])
        self.assertEqual(decoded.records, (source[8:28], source[28:48]))

    def test_normalizer_scales_only_xyz(self):
        source = archive((self.record(1000000, -2000000, 3000000, (7, 9)),))
        result = normalize_collision_trigger_archive(source).encode()
        self.assertEqual(result[:8], source[:8])
        self.assertEqual(struct.unpack_from('<5i', result, 8)[3:],
                         (7, 9))
        self.assertNotEqual(result[8:20], source[8:20])

    def test_invalid_header_and_record_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            decode_collision_trigger_archive(b'1234567')
        valid = archive((self.record(),))
        with self.assertRaises(ValueError):
            decode_collision_trigger_archive(valid[:-1])
        with self.assertRaises(ValueError):
            decode_collision_trigger_archive(valid + b'padding')

    def test_loader_stops_after_first_missing_resource(self):
        sources = tuple(archive((self.record(i, i + 1, i + 2),))
                        for i in range(7))
        loaded = load_collision_trigger_archives(
            (sources[0], sources[1], None, *sources[3:]))
        self.assertEqual(loaded.loaded_count, 2)
        self.assertEqual(len(loaded.resources), 7)
        self.assertIsNotNone(loaded.resources[0])
        self.assertIsNotNone(loaded.resources[1])
        self.assertEqual(loaded.resources[2:], (None,) * 5)

    def test_loader_requires_the_seven_resource_positions(self):
        with self.assertRaises(ValueError):
            load_collision_trigger_archives(())


if __name__ == '__main__':
    unittest.main()
