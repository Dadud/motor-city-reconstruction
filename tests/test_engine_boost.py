"""Focused regressions for the recovered boost scratch helper."""
import math
import struct
import unittest

from client.engine_boost import update_boost_state


def fixture(mode):
    configuration = bytearray(1004)
    struct.pack_into('<h', configuration, 0x3c4, mode)
    for offset, value in ((0x3c8, 1.4), (0x3cc, .8), (0x3d0, 100.),
                          (0x3d4, 2.), (0x3d8, 8.), (0x3dc, 10.),
                          (0x3e0, .5), (0x3e4, .8), (1000, 100.)):
        struct.pack_into('<f', configuration, offset, value)
    state = bytearray(0x10c)
    for offset, value in ((0xf0, 70.), (0xf4, 400.), (0xf8, 540.),
                          (0xfc, 5000.), (0x100, 2.)):
        struct.pack_into('<f', state, offset, value)
    return bytes(configuration), bytes(state)


class BoostHelperTests(unittest.TestCase):
    # Independent Python outputs for the fixture; native byte comparison lives
    # in tools/verify_engine_boost.py because it needs the optional oracle.
    EXPECTED_PYTHON = {
        1: (0x4432da31, 0x40fd70a4, 0, 0),
        2: (0x44142909, 0x40fd70a4, 0x4098c68f, 0x413e4331),
        3: (0x4407079b, 0x3c212ee7, 0x3c309a1c, 0x3cdbef66),
    }

    def test_mode_zero_preserves_entire_scratch_record(self):
        configuration, state = fixture(0)
        self.assertEqual(update_boost_state(configuration, state), state)

    def test_modes_write_finite_state_in_documented_fields(self):
        for mode in (1, 2, 3):
            with self.subTest(mode=mode):
                configuration, state = fixture(mode)
                output = update_boost_state(configuration, state)
                self.assertEqual(output[:0xf8], state[:0xf8])
                self.assertEqual(output[0xfc:0x100], state[0xfc:0x100])
                self.assertTrue(all(math.isfinite(value) for value in
                    struct.unpack_from('<4f', output, 0xf8)))
                self.assertEqual(struct.unpack_from('<I', output, 0xf8)[0],
                                 self.EXPECTED_PYTHON[mode][0])
                self.assertEqual(struct.unpack_from('<I', output, 0x100)[0],
                                 self.EXPECTED_PYTHON[mode][1])
                if mode == 1:
                    self.assertEqual(struct.unpack_from('<2I', output, 0x104), (0, 0))

    def test_native_power_rounding_gap_is_confined_to_mode_three_work(self):
        configuration, state = fixture(3)
        output = update_boost_state(configuration, state)
        # Python libm versus the target's x87 power path; pending exact x87 emulation.
        self.assertEqual(tuple(struct.unpack_from('<2I', output, 0x104)),
                         self.EXPECTED_PYTHON[3][2:])

    def test_invalid_extent_and_mode_are_rejected(self):
        configuration, state = fixture(0)
        with self.assertRaises(ValueError):
            update_boost_state(configuration[:-1], state)
        invalid = bytearray(configuration)
        struct.pack_into('<h', invalid, 0x3c4, 4)
        with self.assertRaisesRegex(ValueError, 'mode'):
            update_boost_state(invalid, state)
