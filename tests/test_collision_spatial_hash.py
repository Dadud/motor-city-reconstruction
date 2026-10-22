import struct
import unittest

from client.collision_spatial_hash import (mark_sphere_neighbors,
                                           mark_spatial_hash_neighbors,
                                           rebuild_collision_spatial_flags,
                                           sphere_overlap)


def body(position=(0., 0., 0.), radius=1., active=0):
    image = bytearray(0x4f8)
    image[4] = active
    struct.pack_into('<3f', image, 8, *position)
    struct.pack_into('<f', image, 0xd8, radius)
    return image


class CollisionSpatialHashTests(unittest.TestCase):
    def test_inclusive_sphere_boundary_and_outside(self):
        owner = body(radius=1.)
        self.assertTrue(sphere_overlap(owner, body((2., 0., 0.), 1.)))
        self.assertFalse(sphere_overlap(owner, body((2.0001, 0., 0.), 1.)))

    def test_marks_only_inactive_overlapping_non_owner_entries(self):
        owner = body(radius=1.)
        touching = body((1.5, 0., 0.), .5)
        distant = body((4., 0., 0.), 1.)
        active = body((0., 0., 0.), 1., active=1)
        result = mark_sphere_neighbors(owner, [owner, touching, distant, active])
        self.assertEqual(result, 1)
        self.assertEqual((owner[4], touching[4], distant[4], active[4]), (0, 1, 0, 1))

    def test_rejects_truncated_images(self):
        with self.assertRaises(ValueError):
            sphere_overlap(bytearray(0xdb), body())
        with self.assertRaises(ValueError):
            mark_sphere_neighbors(body(), [bytearray(0xdc)])

    def test_nine_cell_pass_scans_self_and_nonnegative_neighbors(self):
        owner = body(radius=1.)
        owner[4] = 1
        struct.pack_into('<I', owner, 0x374, 2)
        same_cell = body((1., 0., 0.), .5)
        neighbor = body((0., 2., 0.), 1.)
        missing_cell_only = body((0., 0., 0.), 100.)
        cells = {2: (owner, same_cell), 3: (neighbor,), 4: (missing_cell_only,)}
        before = mark_spatial_hash_neighbors(
            (owner,), cells, {2: (3, -1, -1, -1, -1, -1, -1, -1)})
        self.assertEqual(before, 2)
        self.assertEqual((same_cell[4], neighbor[4], missing_cell_only[4]), (1, 1, 0))

    def test_rebuild_links_and_marks_active_roster_overlaps(self):
        owner = body(radius=1., active=1)
        struct.pack_into('<I', owner, 0x374, 2)
        struct.pack_into('<f', owner, 0x350, 2.)
        candidate = body((1., 0., 0.), .5)
        struct.pack_into('<I', candidate, 0x374, 2)
        struct.pack_into('<3f', candidate, 0x14, 2., 3., 4.)
        slots = {2: (3, -1, -1, -1, -1, -1, -1, -1),
                 3: (-1,) * 8}
        groups = rebuild_collision_spatial_flags(
            [owner, candidate], [owner], slots, body_addresses=(0x1000, 0x2000))
        self.assertEqual((owner[4], candidate[4]), (1, 1))
        self.assertEqual(struct.unpack_from('<I', owner, 0x4f4)[0], 0)
        self.assertEqual(struct.unpack_from('<I', candidate, 0x4f4)[0], 0x1000)
        self.assertEqual([id(body) for body in groups[2]], [id(candidate), id(owner)])

    def test_inactive_records_clear_cached_motion_after_pass(self):
        inactive = body(active=0)
        for index, offset in enumerate((0x14, 0x18, 0x1c, 0x38, 0x3c, 0x40), 1):
            struct.pack_into('<f', inactive, offset, float(index))
        struct.pack_into('<I', inactive, 0x374, 0)
        rebuild_collision_spatial_flags(
            [inactive], [], {0: (-1,) * 8}, body_addresses=(0x1000,))
        self.assertEqual(struct.unpack_from('<6f', inactive, 0x14), (0.,) * 6)

    def test_dynamic_candidate_gate_and_record_center_activate_overlap(self):
        candidate = body((.5, 0., 0.), 1.)
        struct.pack_into('<I', candidate, 0x374, 2)
        record = bytearray(0x78)
        struct.pack_into('<3f', record, 0, 0., 0., 0.)
        struct.pack_into('<I', record, 0x30, 1)
        struct.pack_into('<I', record, 0x38, 2)
        struct.pack_into('<f', record, 0x48, .5)
        struct.pack_into('<I', record, 0x74, 0x11223344)
        slots = {2: (-1,) * 8}
        rebuild_collision_spatial_flags(
            [candidate], [], slots, [record], body_addresses=(0x3000,))
        self.assertEqual(candidate[4], 1)

        gated = body((.5, 0., 0.), 1.)
        struct.pack_into('<I', gated, 0x374, 2)
        struct.pack_into('<I', record, 0x30, 0)
        rebuild_collision_spatial_flags(
            [gated], [], slots, [record], body_addresses=(0x4000,))
        self.assertEqual(gated[4], 0)


if __name__ == '__main__':
    unittest.main()
