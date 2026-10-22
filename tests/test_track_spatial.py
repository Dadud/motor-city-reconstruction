import struct
import unittest
from client.track_spatial import Node, SpatialIndex, decode_spatial
from client.track_mesh import decode_track_with_spatial


def fixture():
    grid = bytearray(4096 * 16)
    struct.pack_into('<4I', grid, 0, 1, 0, 0, 0)
    struct.pack_into('<4I', grid, 16, 0xdeadbeef, 1, 0, 0)
    return struct.pack('<4f', -10, -20, 10, 20) + grid + struct.pack('<4I3I', 0xdeadbeef, 2, 0, 0, 7, 9, 11)


class SpatialTests(unittest.TestCase):
    def test_mesh_spatial_handoff_api(self):
        data = fixture()
        # A minimal valid FRD header/track is impractical here; exercise the
        # public handoff with patched mesh decoder to isolate trailer routing.
        import client.track_mesh as mesh
        original = mesh.decode_mesh
        try:
            mesh.decode_mesh = lambda source, materials=False: ('mesh', 0)
            model, spatial, end = decode_track_with_spatial(data)
        finally:
            mesh.decode_mesh = original
        self.assertEqual(model, 'mesh')
        self.assertEqual(end, len(data))
        self.assertEqual(spatial.cells[0].children[0].identifiers, (7, 9))

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
