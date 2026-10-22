import struct
import unittest
from client.track_spatial import (Node, SpatialIndex, decode_relocated_spatial,
                                  decode_spatial)
from client.world_grid import fixup_world_grid
from client.track_mesh import decode_track_world, decode_track_with_spatial


def fixture():
    grid = bytearray(4096 * 16)
    struct.pack_into('<4I', grid, 0, 1, 0, 0, 0)
    struct.pack_into('<4I', grid, 16, 0xdeadbeef, 1, 0, 0)
    return struct.pack('<4f', -10, -20, 10, 20) + grid + struct.pack('<4I3I', 0xdeadbeef, 2, 0, 0, 7, 9, 11)


class SpatialTests(unittest.TestCase):
    def test_mesh_spatial_handoff_api(self):
        import client.track_mesh as mesh_module
        data = bytearray(16 + 4096 * 16)
        struct.pack_into('<4f', data, 0, -10., -20., 10., 20.)
        for offset in range(16, len(data), 16):
            struct.pack_into('<4I', data, offset, 0xdeadbeef, 0, 0, 0)
        mesh = object()
        original = mesh_module.decode_mesh
        try:
            mesh_module.decode_mesh = lambda source, materials=False: (mesh, 0)
            world = decode_track_world(data)
            model, spatial, end = decode_track_with_spatial(data)
        finally:
            mesh_module.decode_mesh = original
        self.assertIs(world.mesh, mesh)
        self.assertEqual(world.end_offset, len(data))
        self.assertEqual(world.grid.bounds, world.spatial.bounds)
        self.assertEqual(world.spatial.cells[0].identifiers, ())
        self.assertIs(model, mesh)
        self.assertEqual(spatial, world.spatial)
        self.assertEqual(end, world.end_offset)

    def test_query_axis_order_quadrants_and_bounds(self):
        empty = Node((), ())
        cells = [empty]*4096
        leaves = tuple(Node((i,), ()) for i in range(4))
        cells[2*64+3] = Node(None, leaves)
        index = SpatialIndex((0, 0, 64, 64), tuple(cells))
        for x,z,expected in ((2.25,3.25,0),(2.75,3.25,1),(2.25,3.75,2),(2.75,3.75,3)):
            self.assertEqual(index.candidates(x,z),(expected,))
        self.assertEqual(index.candidates(3.25,2.25),())
        self.assertEqual(index.candidates(-1,0),())
        self.assertEqual(index.candidates(64,0),())
        with self.assertRaisesRegex(ValueError,'non-finite'):
            index.candidates(float('inf'),0)

    def test_nested_and_root_leaves_follow_stream_order(self):
        data = fixture()
        index, end = decode_spatial(data, 0)
        self.assertEqual(end, len(data))
        self.assertEqual(index.cells[0].children[0].identifiers, (7, 9))
        self.assertEqual(index.cells[1].identifiers, (11,))

    def test_relocated_tree_matches_file_layout_tree(self):
        data = fixture()
        image_address = 0x71000000
        grid_offset = 0
        expected, end = decode_spatial(data, grid_offset)
        relocated = fixup_world_grid(data, image_address)
        actual = decode_relocated_spatial(relocated.bounds, relocated.table,
                                          relocated.payload, image_address)
        self.assertEqual(actual, expected)
        self.assertEqual(end, len(data))

    def test_truncation_and_identifier_budget(self):
        with self.assertRaisesRegex(ValueError, 'EOF'):
            decode_spatial(fixture()[:-1], 0)
        data = bytearray(fixture())
        struct.pack_into('<I', data, 16 + 20, 4_000_001)
        with self.assertRaisesRegex(ValueError, 'budget'):
            decode_spatial(data, 0)

    def test_invalid_bounds(self):
        data = bytearray(fixture())
        struct.pack_into('<f', data, 0, float('nan'))
        with self.assertRaisesRegex(ValueError, 'bounds'):
            decode_spatial(data, 0)
