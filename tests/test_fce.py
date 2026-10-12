import math
import struct
import unittest
from client.fce import HEADER, decode


def fixture():
    data = bytearray(HEADER + 72 + 56)
    struct.pack_into('<4I', data, 0, 0x101015, 0, 1, 3)
    struct.pack_into('<3I', data, 0x14, 0, 36, 72)
    struct.pack_into('<I', data, 0x11c, 1)
    struct.pack_into('<3f', data, 0x120, 10, 20, 30)
    struct.pack_into('<I', data, 0x520, 3)
    struct.pack_into('<I', data, 0x720, 1)
    data[0xe28:0xe2e] = b':Hbody'
    struct.pack_into('<9f', data, HEADER, 0, 0, 0, 1, 0, 0, 0, 1, 0)
    struct.pack_into('<9f', data, HEADER+36, 0, 0, 1, 0, 0, 1, 0, 0, 1)
    struct.pack_into('<4I', data, HEADER+72, 2, 0, 1, 2)
    struct.pack_into('<I', data, HEADER+72+28, 4)
    struct.pack_into('<6f', data, HEADER+72+32, 0, 1, 0, 0, 0, 1)
    return data


class GeometryTests(unittest.TestCase):
    def test_layout_and_local_indices(self):
        model = decode(fixture())
        part = model.parts[0]
        self.assertEqual(part.name, ':Hbody')
        self.assertEqual(part.origin, (10, 20, 30))
        self.assertEqual(part.vertices[1], (1, 0, 0))
        self.assertEqual(part.triangles[0].indices, (0, 1, 2))
        self.assertEqual(part.triangles[0].texture_page, 2)
        self.assertEqual(part.triangles[0].flags, 4)
        self.assertEqual(model.triangle_count, 1)

    def test_truncated_table(self):
        with self.assertRaisesRegex(ValueError, 'EOF'):
            decode(fixture()[:-1])

    def test_local_index_outside_part(self):
        data = fixture()
        struct.pack_into('<I', data, HEADER+72+4, 3)
        with self.assertRaisesRegex(ValueError, 'index outside'):
            decode(data)

    def test_overlapping_tables(self):
        data = fixture()
        struct.pack_into('<I', data, 0x18, 0)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            decode(data)

    def test_invalid_part_range(self):
        data = fixture()
        struct.pack_into('<I', data, 0x420, 3)
        with self.assertRaisesRegex(ValueError, 'part outside'):
            decode(data)

    def test_nan_position_is_rejected(self):
        data = fixture()
        struct.pack_into('<f', data, HEADER, float('nan'))
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            decode(data)

    def test_nan_normal_is_rebuilt_from_geometry(self):
        data = fixture()
        struct.pack_into('<f', data, HEADER+36, float('nan'))
        model = decode(data)
        self.assertTrue(model.warnings)
        self.assertEqual(model.parts[0].normals[0], (0, 0, 1))
        self.assertTrue(all(math.isfinite(x) for n in model.parts[0].normals for x in n))

    def test_unknown_version_and_invalid_part_count(self):
        data = fixture()
        struct.pack_into('<I', data, 0, 0)
        with self.assertRaisesRegex(ValueError, 'version'):
            decode(data)
        data = fixture()
        struct.pack_into('<I', data, 0x11c, 65)
        with self.assertRaisesRegex(ValueError, 'part count'):
            decode(data)
