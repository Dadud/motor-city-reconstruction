import struct
import tempfile
import unittest
from pathlib import Path

from client.assets import Assets
from client.sky import (load_sky_resources, sky_resource_names,
                        sky_material_triangle_indices,
                        sky_material_normalize_grid, sky_material_random_grid,
                        sky_material_smooth_grid, sky_material_mesh_outputs)
from client.random_state import RandomState


def fsh(entries):
    """Build a small SHPI archive containing uncompressed BGRA images."""
    directory_size = 16 + len(entries) * 8
    payloads, offsets = [], []
    cursor = directory_size
    for name, width, height, bgra in entries:
        payload = struct.pack('<IHH', 0x7d, width, height) + b'\0' * 8 + bgra
        payloads.append(payload)
        offsets.append(cursor)
        cursor += len(payload)
    result = bytearray(b'SHPI' + struct.pack('<II', cursor, len(entries)) + b'\0' * 4)
    for (name, _, _, _), offset in zip(entries, offsets):
        result.extend(name.encode('ascii').ljust(4, b' ')[:4])
        result.extend(struct.pack('<I', offset))
    return bytes(result) + b''.join(payloads)


class SkyResourceTests(unittest.TestCase):
    def test_material_random_grid_uses_native_transposed_storage(self):
        seed = (0xf22d0e56, 0x883126e9, 0xc624dd2f,
                0x0702c49c, 0x9e353f7d, 0x6fdf3b64)
        state = RandomState(seed)
        grid = sky_material_random_grid(state, upper_bound=64, modulus=8)
        self.assertEqual((grid[0], grid[26], grid[52], grid[1]),
                         (59.0, 59.0, 64.0, 58.0))
        self.assertEqual(len(grid), 676)

    def test_material_height_normalization(self):
        grid = [128.0] * 676
        grid[0], grid[1], grid[2] = 0.0, 64.0, 255.0
        normalized = sky_material_normalize_grid(grid)
        self.assertEqual(normalized[0], 0.0)
        self.assertAlmostEqual(normalized[1], 37.3438835, places=5)
        self.assertGreater(normalized[2], 254.0)

    def test_material_smoothing_preserves_midpoint_field(self):
        grid = sky_material_smooth_grid([128.0] * 676, upper_bound=255)
        self.assertEqual(grid, (128.0,) * 676)

    def test_material_mesh_outputs_pack_grayscale(self):
        positions, mesh = sky_material_mesh_outputs(
            [128.0] * 676, angle=0.0, row_scale=2.0, column_scale=4.0,
            base_offset=1.0, amplitude=0.0, color_scale=1.0)
        self.assertEqual(len(positions), 676)
        self.assertEqual(len(mesh), 676)
        self.assertEqual(mesh[0], (0.0, 0.0, 0x80808080))
        self.assertEqual(mesh[27], (2.0, 1.0, 0x80808080))


    def test_material_triangle_index_topology(self):
        indices = sky_material_triangle_indices()
        self.assertEqual(len(indices), 25 * 25 * 2)
        self.assertEqual(indices[:8], (0, 26, 1, 27, 2, 28, 3, 29))
        self.assertEqual(indices[-2:], (648, 674))
        self.assertTrue(all(0 <= index < 26 * 26 for index in indices))

    def test_exact_native_table_order_for_each_mode(self):
        self.assertEqual(sky_resource_names(),
                         ('CLDD', 'CLD2', 'CHRD', 'SUND', 'VAMD', 'VMD2', 'HDC%d', None))
        self.assertEqual(sky_resource_names(wet=True),
                         ('CLWD', 'CL2W', 'CHRW', 'SUNW', 'VADW', 'VDW2', 'HDW%d', 'CLDD'))
        self.assertEqual(sky_resource_names(night=True),
                         ('CLDN', 'CL2N', 'CHRN', 'SUNN', 'VAMN', 'VMN2', 'HNC%d', 'CLWD'))
        self.assertEqual(sky_resource_names(night=True, wet=True),
                         ('CLWN', 'C2WN', 'CHNW', 'SNNW', 'VMNW', 'VNW2', 'HNW%d', 'CLDN'))

    def test_native_26_grid_uses_dimension_over_26_and_clamps(self):
        width = height = 27
        bgra = bytearray()
        for y in range(height):
            for x in range(width):
                bgra.extend((x, y, 0, 255))
        archive = fsh([('VAMD', width, height, bytes(bgra))])
        resources = load_sky_resources(archive)
        grid = resources.lookups[0]
        self.assertEqual(grid.name, 'VAMD')
        self.assertEqual(grid.table_index, 4)
        self.assertEqual(len(grid.rgba), 26 * 26 * 4)
        # Native width/26 scaling reaches and clamps at the last source pixel.
        self.assertEqual(grid.rgba[:4], bytes((0, 0, 0, 255)))
        self.assertEqual(grid.rgba[-4:], bytes((0, 26, 26, 255)))
        self.assertIsNone(resources.lookups[2])

    def test_cloud_template_expansion_stops_at_first_missing_image(self):
        image = bytes((0, 0, 0, 255))
        archive = fsh([
            ('HDC0', 1, 1, image), ('HDC1', 1, 1, image),
            ('HDC3', 1, 1, image),
        ])
        resources = load_sky_resources(archive, cloud_count=4)
        self.assertEqual(resources.cloud_pattern, 'HDC%d')
        self.assertEqual(resources.clouds, ('HDC0', 'HDC1'))
        self.assertEqual(load_sky_resources(archive, cloud_count=4,
                                            clouds_enabled=False).clouds, ())
        lower_case = fsh([('hdc0', 1, 1, image)])
        self.assertEqual(load_sky_resources(lower_case, cloud_count=1).clouds, ())

    def test_assets_loads_case_insensitive_track_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            track = Path(tmp) / 'Data' / 'Tracks' / 'TrackA'
            track.mkdir(parents=True)
            (track / 'Sky.FSH').write_bytes(fsh([]))
            assets = Assets(tmp)
            self.assertIsNotNone(assets.load_sky_resources('tracka'))
            self.assertIsNone(assets.load_sky_resources('missing'))
            with self.assertRaises(ValueError):
                assets.load_sky_resources('../outside')

    def test_rejects_invalid_mode_and_cloud_count(self):
        with self.assertRaises(ValueError):
            sky_resource_names(night=1)
        for count in (-1, 257, True):
            with self.assertRaises(ValueError):
                load_sky_resources(fsh([]), cloud_count=count)


if __name__ == '__main__':
    unittest.main()
