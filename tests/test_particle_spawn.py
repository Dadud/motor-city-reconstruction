import struct
import unittest

from client.particle_spawn import POOL_CAPACITY, RECORD_BYTES, construct_particle
from client.random_state import RandomState


def _config():
    config = bytearray(0x60)
    struct.pack_into('<h', config, 8, 10)
    struct.pack_into('<i', config, 0xc, 0)
    for offset in (0x10, 0x14, 0x18, 0x1c, 0x30, 0x34,
                   0x38, 0x40, 0x44, 0x48):
        struct.pack_into('<f', config, offset, 1.0)
    struct.pack_into('<4I', config, 0x20, 11, 12, 13, 0xffaabbcc)
    config[0x5c] = 7
    return bytes(config)


class ParticleSpawnTests(unittest.TestCase):
    def test_constructs_first_slot_and_advances_rng(self):
        pool = [bytearray(RECORD_BYTES) for _ in range(POOL_CAPACITY)]
        rng = RandomState((0xf22d0e56, 0x883126e9, 0xc624dd2f,
                           0x0702c49c, 0x9e353f7d, 0x6fdf3b64))
        index = construct_particle(_config(), 0x12345678, (10, 20, 30), 1.0,
                                  (0., 0., 0.), (0., 0., 0.), (0., 0., 0.),
                                  rng, pool)
        self.assertEqual(index, 0)
        self.assertEqual(struct.unpack_from('<I', pool[0], 0)[0], 0x12345678)
        self.assertEqual(struct.unpack_from('<3i', pool[0], 0xc), (10, 20, 30))
        self.assertEqual(struct.unpack_from('<h', pool[0], 4)[0], 10)
        self.assertEqual(rng.words, (0xeae8d5ee, 0x6bcd9603, 0x6368ac4a,
                                     0xe99220e4, 0x3d70a3e4, 0x6fdf3b6a))

    def test_global_mode_gate_does_not_mutate_state_or_pool(self):
        pool = [bytearray(RECORD_BYTES) for _ in range(POOL_CAPACITY)]
        rng = RandomState((1, 2, 3, 4, 5, 6))
        before = tuple(rng.words)
        self.assertIsNone(construct_particle(
            _config(), 0x12345678, (0, 0, 0), 1.0, (0.,) * 3, (0.,) * 3,
            (0.,) * 3, rng, pool, effect_mode=2))
        self.assertEqual(rng.words, before)
        self.assertFalse(any(any(slot) for slot in pool))


if __name__ == '__main__':
    unittest.main()
