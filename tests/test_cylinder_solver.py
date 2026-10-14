"""Core-driver regressions using an authored synthetic record."""
import math
import struct
import unittest
from client.cylinder_solver import solve_core_record


def synthetic_record():
    record=bytearray(1004)
    for offset,value in ((0x6e,1),(0x7a,1),(0x84,1),(0x94,8),
                         (0xa4,600),(0xa6,4),(0x2dc,1),(0x310,1),(0x312,1)):
        struct.pack_into('<h',record,offset,value)
    for offset,value in ((0x70,1),(0x7c,1),(0x8c,4),(0x90,3.5),
        (0x98,2),(0x9c,1.6),(0xa0,9),(0xa8,66),(0xac,10),(0xb0,12),
        (0xb4,62),(0xb8,.2614174485206604),(0xbc,.24842533469200134),
        (0x314,2),(0x318,28),(0x31c,1.6),(0x320,28)):
        struct.pack_into('<f',record,offset,value)
    for offset in (0x34c,0x39c):
        struct.pack_into('<8f',record,offset,*(.1*i for i in range(1,9)))
    for offset in (0x324,0x374):
        struct.pack_into('<8f',record,offset,*(40*i for i in range(1,9)))
    return bytes(record)


class CoreSolverTests(unittest.TestCase):
    def test_unboosted_record_and_output_extent(self):
        record=synthetic_record()
        output=solve_core_record(record)
        self.assertEqual(output[:0xc4],record[:0xc4])
        self.assertEqual(output[0x2d8:],record[0x2d8:])
        for offset in (0xc4,0x110,0x15c,0x1a8,0x1f4,0x240,0x28c):
            self.assertTrue(all(math.isfinite(v) for v in struct.unpack_from('<19f',output,offset)))
        self.assertGreater(max(struct.unpack_from('<19f',output,0x110)),0)
        # Bounded original CPU results; later pressures exercise prior-knot fill.
        self.assertEqual(struct.unpack_from('<3f',output,0xc4),
                         (108.43608856201172,133.40232849121094,148.99156188964844))
        self.assertEqual(struct.unpack_from('<3f',output,0x15c),
                         (14.65725326538086,14.6390962600708,14.610742568969727))

    def test_boost_is_explicitly_unsupported(self):
        record=bytearray(synthetic_record())
        for mode in (1,2,3):
            struct.pack_into('<h',record,0x3c4,mode)
            with self.assertRaisesRegex(ValueError,'boosted'):
                solve_core_record(bytes(record))

    def test_invalid_record_and_geometry(self):
        for record in (bytes(1003),bytearray(1004)):
            with self.assertRaises(ValueError):
                solve_core_record(record)
        record=bytearray(synthetic_record())
        struct.pack_into('<f',record,0x8c,float('nan'))
        with self.assertRaises(ValueError):
            solve_core_record(bytes(record))

    def test_malformed_angles_are_bounded(self):
        for value in (1e30, -1e30, float('inf'), float('nan')):
            record=bytearray(synthetic_record())
            struct.pack_into('<f',record,0xa8,value)
            with self.assertRaises(ValueError):
                solve_core_record(bytes(record))
