import struct
import unittest

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES
from client.particle_update import (TRAIL_CAPACITY, TRAIL_RECORD_BYTES,
                                    advance_particle_motion,
                                    advance_particle_trails)


class ParticleUpdateTests(unittest.TestCase):
    def test_motion_integrates_only_active_records_after_elapsed_ticks(self):
        pool = [bytearray(RECORD_BYTES) for _ in range(POOL_CAPACITY)]
        slot = pool[0]
        struct.pack_into('<Ih', slot, 0, 0x1234, 3)
        struct.pack_into('<3f', slot, 0xc, 10., 20., 30.)
        struct.pack_into('<3f', slot, 0x18, 1., 0.5, -2.)
        struct.pack_into('<f', slot, 0x24, 2.)
        struct.pack_into('<f', slot, 0x2c, 0.5)
        struct.pack_into('<f', slot, 0x30, 3.)
        struct.pack_into('<f', slot, 0x34, 1.)
        self.assertEqual(advance_particle_motion(pool, {0x1234: 2.}, 4, 1), 2)
        self.assertEqual(struct.unpack_from('<3f', slot, 0xc),
                         (10.03125, 20.078125, 29.9375))
        self.assertEqual(struct.unpack_from('<3f', slot, 0x18), (1., 2.5, -2.))
        self.assertEqual(struct.unpack_from('<f', slot, 0x24)[0], 2.5)
        self.assertEqual(struct.unpack_from('<f', slot, 0x30)[0], 4.)
        self.assertFalse(any(pool[1]))

    def test_trail_progress_zero_expires_and_counts_type(self):
        records = [bytearray(TRAIL_RECORD_BYTES) for _ in range(TRAIL_CAPACITY)]
        definition = bytearray(0x84)
        struct.pack_into('<i', definition, 0, 3)
        struct.pack_into('<i', definition, 0x70, 10)
        definition[0x83] = 1
        struct.pack_into('<Ii', records[0], 0, 0x1234, 1)
        counts = [0] * 26
        advance_particle_trails(records, {0x1234: bytes(definition)}, counts)
        self.assertEqual(struct.unpack_from('<i', records[0], 4)[0], 0)
        self.assertEqual(records[0][0x2b], 0)
        self.assertEqual(counts[3], 1)


if __name__ == '__main__':
    unittest.main()
