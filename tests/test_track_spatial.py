import struct
import unittest
from client.track_spatial import (Node, SpatialIndex, decode_relocated_spatial,
                                  decode_spatial)
from client.world_grid import fixup_world_grid
from client.track_mesh import decode_track_world, decode_track_with_spatial
from client.track_checksum import track_checksum


def fixture():
    grid = bytearray(4096 * 16)
    struct.pack_into('<4I', grid, 0, 1, 0, 0, 0)
    struct.pack_into('<4I', grid, 16, 0xdeadbeef, 1, 0, 0)
    return struct.pack('<4f', -10, -20, 10, 20) + grid + struct.pack('<4I3I', 0xdeadbeef, 2, 0, 0, 7, 9, 11)


class SpatialTests(unittest.TestCase):
    def test_mesh_spatial_handoff_api(self):
        import client.track_mesh as mesh_module
        track_data = bytearray(56 + 84 * 2)
        struct.pack_into('<I', track_data, 0, 0xfeeeeb19)
        struct.pack_into('<II', track_data, 44, 0, 2)
        for index in range(2):
            struct.pack_into('<14f', track_data, 56 + index * 84,
                             0, 0, index, 0, 1, 0, 0, 0, 1, 1, 0, 0, 3, 4)
        block_header = bytearray(0x6c4)
        trailer = bytearray(16 + 4096 * 16)
        struct.pack_into('<4f', trailer, 0, -10., -20., 10., 20.)
        for offset in range(16, len(trailer), 16):
            struct.pack_into('<4I', trailer, offset, 0xdeadbeef, 0, 0, 0)
        material_counts = bytes(8)
        mesh = object()
        original = mesh_module.decode_mesh
        try:
            mesh_end = len(track_data) + len(block_header) + len(material_counts)
            mesh_module.decode_mesh = lambda source, materials=False, **kwargs: (mesh, mesh_end)
            combined = track_data + block_header + material_counts + trailer
            world = decode_track_world(combined)
            model, spatial, end = decode_track_with_spatial(combined)
        finally:
            mesh_module.decode_mesh = original
        self.assertIs(world.mesh, mesh)
        self.assertEqual(world.end_offset, len(combined))
        self.assertEqual(world.grid.bounds, world.spatial.bounds)
        self.assertEqual(world.spatial.cells[0].identifiers, ())
        self.assertEqual(len(world.block_headers), 1)
        self.assertIsNotNone(world.query_world)
        self.assertEqual(world.loader_checksum, track_checksum(combined))
        self.assertEqual(world.query_world.path_count, 2)
        self.assertEqual(world.query_world.last_block, 0)
        self.assertEqual(world.object_sections, ((0, (0, 0, 0, 0)),))
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

    def test_installed_track_world_retains_block_header_counts(self):
        from pathlib import Path
        from client.track_mesh import decode_track_world
        candidates = sorted(Path(r'C:\Program Files (x86)\EA Games\Motor City Online\Data\Tracks').rglob('Tr.frd'))
        if not candidates:
            self.skipTest('installed MCO track corpus is unavailable')
        track_data = candidates[0].read_bytes()
        world = decode_track_world(track_data)
        from client.track import decode_track
        from client.track_surface_lookup import track_surface_lookup
        query_world = world.query_world
        self.assertIsNotNone(query_world)
        track = decode_track(track_data)
        self.assertEqual(query_world.path_count, len(track.slices))
        self.assertEqual(len(world.block_headers), len(world.object_sections))
        self.assertTrue(world.block_headers)
        self.assertTrue(any(sum(counts) for _, counts in world.object_sections))
        self.assertEqual(sum(len(group.objects) for group in world.objects),
                         sum(sum(counts) for _, counts in world.object_sections))
        self.assertTrue(world.objects)
        self.assertEqual(len(world.object_meshes), len(world.objects))
        self.assertEqual(sum(len(model.parts) for model in world.object_meshes),
                         sum(len(group.objects) for group in world.objects))
        self.assertGreater(sum(model.triangle_count for model in world.object_meshes), 0)
        at_quality_zero = world.object_meshes_at_quality(0)
        self.assertEqual(sum(len(model.parts) for model in at_quality_zero),
                         sum(len(model.parts) for model in world.object_meshes))
        at_quality_four = world.object_meshes_at_quality(4)
        self.assertLessEqual(sum(len(model.parts) for model in at_quality_four),
                             sum(len(model.parts) for model in at_quality_zero))
        static_models = world.object_meshes_at_quality(0, include_animated=False)
        expected_static = sum(1 for group in world.objects for obj in group.objects
                              if (obj.descriptor[2] & 0xf) != 3)
        self.assertEqual(sum(len(model.parts) for model in static_models),
                         expected_static)
        poses = world.sample_object_poses(0)
        self.assertEqual(tuple(map(len, poses)),
                         tuple(len(group.objects) for group in world.objects))
        self.assertTrue(any(pose is not None for group in poses for pose in group))
        point = track.slices[0].position
        record = bytearray(0x44)
        track_surface_lookup(query_world, point, record)
        block = struct.unpack_from('<I', record, 4)[0]
        descriptor = struct.unpack_from('<I', record, 12)[0]
        block_base = query_world.blocks_address + block * 0x6c4
        if descriptor:
            descriptor_base = query_world.memory.word(block_base + 0x67c)
            descriptor_count = query_world.memory.word(block_base + 0x660)
            self.assertGreaterEqual(descriptor, descriptor_base)
            self.assertLessEqual(descriptor + 20, descriptor_base + descriptor_count * 20)
            for vertex in struct.unpack_from('<4I', record, 16):
                vertex_base = query_world.memory.word(block_base + 0x14c)
                vertex_count = query_world.memory.word(block_base + 0x134)
                self.assertGreaterEqual(vertex, vertex_base)
                self.assertLessEqual(vertex + 12, vertex_base + vertex_count * 12)

    def test_installed_track_lighting_percentages_reach_object_vertex_colors(self):
        from pathlib import Path
        from client.collision_palette import adjust_color_words
        from client.track_lighting import read_object_color_percentages
        from client.track_mesh import decode_track_world
        root = Path(r'C:\Program Files (x86)\EA Games\Motor City Online\Data\Tracks')
        candidates = sorted(root.rglob('Tr.frd'))
        selected = next(((frd, frd.with_name('Tr.ini')) for frd in candidates
                         if frd.with_name('Tr.ini').is_file()
                         and read_object_color_percentages(frd.with_name('Tr.ini'))
                         != (100, 100, 100)), None)
        if selected is None:
            self.skipTest('installed non-neutral track lighting fixture is unavailable')
        frd, lighting_file = selected
        percentages = read_object_color_percentages(lighting_file)
        world = decode_track_world(frd.read_bytes(), lighting_file=lighting_file)
        group = next(group for group in world.objects if group.objects)
        obj = group.objects[0]
        expected = bytearray(b''.join(obj.vertex_attributes))
        adjust_color_words(expected, len(obj.vertex_attributes), percentages)
        import struct
        colors = struct.unpack('<' + 'I' * len(obj.vertex_attributes), expected)
        model_index = world.objects.index(group)
        self.assertEqual(world.object_meshes[model_index].parts[0].vertex_colors,
                         colors)
