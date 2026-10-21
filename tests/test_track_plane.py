import struct
import unittest

from client.track_plane import plane_from_query_record, surface_height, track_plane


class TrackPlaneTests(unittest.TestCase):
    def test_first_triangle_plane_and_height(self):
        vertices = ((0, 0, 0), (0, 2, 10), (10, 4, 10), (10, 0, 0))
        point, normal = track_plane(2, 2, vertices)
        self.assertEqual(point, (0.0, 2.0, 10.0))
        self.assertAlmostEqual(sum(v*v for v in normal), 1.0, places=6)
        height = surface_height(normal, point, (2, 0, 8))
        self.assertTrue(0.0 < height < 3.0)

    def test_degenerate_first_triangle_falls_back_to_second(self):
        vertices = ((0, 0, 0), (0, 0, 10), (10, 2, 10), (10, 0, 0))
        _, normal = track_plane(5, 5, vertices)
        self.assertNotEqual(normal, (0.0, 0.0, 0.0))
        self.assertAlmostEqual(sum(v*v for v in normal), 1.0, places=6)

    def test_query_record_reads_native_vertex_pointers(self):
        vertices = ((0, 0, 0), (0, 0, 10), (10, 2, 10), (10, 0, 0))
        memory = {0x1000 + 12*i: struct.pack('<3f', *point)
                  for i, point in enumerate(vertices)}
        record = bytearray(0x2c)
        struct.pack_into('<I', record, 0x0c, 1)
        struct.pack_into('<4I', record, 0x10, 0x1000, 0x100c, 0x1018, 0x1024)
        struct.pack_into('<i', record, 0x20, 5)
        struct.pack_into('<i', record, 0x28, 5)
        point, normal = plane_from_query_record(
            record, read_memory=lambda address, size: memory[address][:size])
        self.assertEqual(point, (0.0, 0.0, 10.0))
        self.assertNotEqual(normal, (0.0, 0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
