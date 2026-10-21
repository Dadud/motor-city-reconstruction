import struct
import unittest

from client.world_object_record import (RECORD_SIZE, update_object_array,
                                       update_object_record,
                                       maintain_object_record,
                                       maintain_object_array)


class WorldObjectRecordTests(unittest.TestCase):
    @staticmethod
    def record(object_id=1, active=True):
        image = bytearray(RECORD_SIZE)
        struct.pack_into('<I', image, 0, object_id)
        image[4] = int(active)
        struct.pack_into('<3f', image, 8, 2.0, -3.0, 1.0)
        struct.pack_into('<3f', image, 0x14, 0.75, -0.25, 0.5)
        struct.pack_into('<3f', image, 0x38, 0.03125, -0.015625, 0.0078125)
        struct.pack_into('<3f', image, 0x5c, 0.25, -0.5, 0.125)
        struct.pack_into('<9f', image, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        struct.pack_into('<3f', image, 0x328, 0.5, -0.25, 1.0)
        struct.pack_into('<66f', image, 0xe0, *((i % 7 - 3) / 8 for i in range(66)))
        return image

    def test_single_record_writes_recovered_outputs_and_preserves_other_bytes(self):
        image = self.record()
        before = bytes(image)
        update_object_record(image, object_phase=0)
        changed = {i for i, (a, b) in enumerate(zip(before, image)) if a != b}
        allowed = set(range(8, 20)) | set(range(0x78, 0xc0)) | \
            set(range(0xc0, 0xcc)) | set(range(0x1e8, 0x2f0))
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)

    def test_inactive_record_is_unchanged(self):
        image = self.record(active=False)
        before = bytes(image)
        self.assertIs(update_object_record(image, object_phase=0), image)
        self.assertEqual(bytes(image), before)

    def test_array_updates_active_rows_in_place_and_keeps_inactive_rows(self):
        first = self.record(1, True)
        second = self.record(2, False)
        before_second = bytes(second)
        array = bytearray(first + second)
        self.assertIs(update_object_array(array, object_phase=0), array)
        self.assertNotEqual(array[:RECORD_SIZE], first)
        self.assertEqual(array[RECORD_SIZE:], before_second)

    def test_rejects_partial_array(self):
        with self.assertRaisesRegex(ValueError, 'whole number'):
            update_object_array(bytearray(RECORD_SIZE + 1), object_phase=0)

    def test_maintenance_runs_physics_on_same_active_record_before_parent_writes(self):
        image = self.record()
        struct.pack_into('<f', image, 0xd8, 1.0)
        struct.pack_into('<f', image, 0x350, 2.0)
        seen = []

        def physics(record):
            seen.append(record)
            struct.pack_into('<3f', record, 0x38, 12.0, 0.0, 0.0)

        self.assertIs(maintain_object_record(image, update_physics=physics), image)
        self.assertEqual(seen, [image])
        self.assertEqual(struct.unpack_from('<3f', image, 0x38), (10.0, 0.0, 0.0))

    def test_inactive_maintenance_skips_physics_and_preserves_record(self):
        image = self.record(active=False)
        before = bytes(image)
        maintain_object_record(image,
                              update_physics=lambda _: self.fail('inactive physics ran'))
        self.assertEqual(bytes(image), before)

    def test_maintenance_array_uses_active_rows_only(self):
        first, second = self.record(1, True), self.record(2, False)
        before_second = bytes(second)
        calls = []
        records = bytearray(first + second)
        maintain_object_array(records, update_physics=lambda row: calls.append(row))
        self.assertEqual(len(calls), 1)
        self.assertEqual(records[RECORD_SIZE:], before_second)


if __name__ == '__main__':
    unittest.main()
