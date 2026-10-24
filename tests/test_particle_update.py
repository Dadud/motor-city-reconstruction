import struct
import unittest

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES
from client.particle_update import (TRAIL_CAPACITY, TRAIL_RECORD_BYTES,
                                    advance_particle_frame_core,
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

    def test_parent_frame_core_scales_and_ages_particles_and_trails(self):
        pool = [bytearray(RECORD_BYTES) for _ in range(POOL_CAPACITY)]
        source = bytearray(0x84)
        struct.pack_into('<i', source, 0, 3)
        struct.pack_into('<f', source, 0x38, 0.5)
        struct.pack_into('<i', source, 0x70, 10)
        source[0x83] = 50
        token = 0x1234
        slot = pool[0]
        struct.pack_into('<Ih', slot, 0, token, 2)
        struct.pack_into('<4f', slot, 0x18, 2., 4., 6., 8.)
        struct.pack_into('<f', slot, 0x34, 6.)
        trails = [bytearray(TRAIL_RECORD_BYTES) for _ in range(TRAIL_CAPACITY)]
        struct.pack_into('<Ii', trails[0], 0, token, 2)
        counts = [99] * 52
        advance_particle_frame_core(pool, {token: bytes(source)}, trails,
                                    counts, 0)
        self.assertEqual(struct.unpack_from('<h', slot, 4)[0], 1)
        self.assertEqual(struct.unpack_from('<4f', slot, 0x18),
                         (1., 2., 3., 8.))
        self.assertEqual(struct.unpack_from('<f', slot, 0x34)[0], 3.)
        self.assertEqual(struct.unpack_from('<i', trails[0], 4)[0], 1)
        self.assertEqual(trails[0][0x2b], 10)
        self.assertEqual(counts[3], 1)
        self.assertEqual(counts[26:], [0] * 26)


if __name__ == '__main__':
    unittest.main()
