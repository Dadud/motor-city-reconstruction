import struct
import unittest

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_surface_sample import sample_track_surface
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, fixture


def _world(arena, root):
    grid = root + bytes(65536 - len(root))
    world = TrackSurfaceWorld(TrackSurfaceMemory(grid, bytes(arena), BASE),
                              (0.0, 0.0), (1.0, 1.0), BLOCKS, PATH, 2, 24)
    return world


class TrackSurfaceSampleTests(unittest.TestCase):
    def test_successful_quad_lookup_writes_sampled_height(self):
        arena, root, query = fixture(2, 0, 0, 0, 7, 8, 8, 1)
        vertices = ((0, 0, 0), (16, 1, 0), (16, 3, 16), (0, -2, 16))
        for block in range(3):
            for index, point in enumerate(vertices):
                struct.pack_into('<3f', arena,
                                 GEOMETRY - BASE + block * 0x200 + index * 12,
                                 *point)
        point = bytearray(struct.pack('<3f', 8, 7, 8))
        self.assertTrue(sample_track_surface(_world(arena, root), query, point, 0))
        self.assertEqual(struct.unpack('<3f', point), (8.0, -0.5, 8.0))
        self.assertNotEqual(struct.unpack_from('<I', query, 12)[0], 0)

    def test_miss_preserves_point_height_and_updates_query_state(self):
        arena, root, query = fixture(0, 0, 0, 0, 0, 8, 8, 2)
        point = bytearray(struct.pack('<3f', 8, 7, 8))
        before = bytes(point)
        self.assertFalse(sample_track_surface(_world(arena, root), query, point, 3))
        self.assertEqual(bytes(point), before)
        self.assertEqual(struct.unpack_from('<i', query, 0)[0], 5)
        self.assertEqual(struct.unpack_from('<i', query, 4)[0], 0)


if __name__ == '__main__':
    unittest.main()
