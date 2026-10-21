import struct
import unittest

from client.collision_geometry import (collision_candidate_point,
                                       probe_collision_candidate)


def make_row(mask=0xffffffff):
    row = bytearray(0x54)
    struct.pack_into('<3f', row, 0, 10.0, 20.0, 30.0)
    struct.pack_into('<3f', row, 0x18, 1.0, 2.0, 3.0)
    struct.pack_into('<3f', row, 0x24, 4.0, 5.0, 6.0)
    struct.pack_into('<2f', row, 0x38, 2.0, 2.0)
    struct.pack_into('<I', row, 0x4c, mask)
    return bytes(row)


def make_owner(index=3, slot=7, active=True):
    owner = bytearray(0xE7C)
    owner[4] = int(active)
    struct.pack_into('<II', owner, 0x370, index, 0)
    struct.pack_into('<I', owner, 0xE78, slot)
    return owner


def probe(owner, *, rows=None, objects=(), traffic=(), sample=None,
          mask_all=True, surface_result=0):
    rows = rows or tuple(make_row(0xffffffff if mask_all else 0)
                         for _ in range(8))
    calls = []

    def sample_surface(point, index):
        calls.append((point, index))
        return (True, 1, 1.0) if sample is None else sample

    result = probe_collision_candidate(
        owner, 3, 0.0, 0.5, path_rows=rows, path_count=8,
        range_start=0, range_end=0, lower_limit=0, upper_limit=0,
        clamp_indices=True, surface_vcall_result=surface_result,
        world_objects=objects, traffic_rows=traffic,
        sample_surface=sample_surface)
    return result, calls


class CollisionGeometryTests(unittest.TestCase):
    def test_candidate_point_uses_track_origin_and_local_axes(self):
        self.assertEqual(collision_candidate_point((make_row(),) * 8, 3, 2, 0.5),
                         (18.5, 31.0, 43.5))

    def test_mask_and_index_filters_short_circuit_surface_sampling(self):
        result, calls = probe(make_owner(), mask_all=False)
        self.assertFalse(result)
        self.assertEqual(calls, [])

        # An enabled range that rejects the candidate also avoids the sampler.
        owner = make_owner()
        rows = (make_row(),) * 8
        result = probe_collision_candidate(
            owner, 6, 0.0, 0.0, path_rows=rows, path_count=8,
            range_start=0, range_end=1, lower_limit=0, upper_limit=4,
            clamp_indices=True, surface_vcall_result=0,
            sample_surface=lambda *_: self.fail('unexpected sample'))
        self.assertFalse(result)

    def test_nearby_active_world_object_rejects_adjacent_path_contact(self):
        owner = make_owner(index=3, slot=7)
        obstacle = make_owner(index=4, slot=8)
        result, calls = probe(owner, objects=(obstacle,))
        self.assertFalse(result)
        self.assertEqual(calls, [])

        obstacle[4] = 0
        result, calls = probe(owner, objects=(obstacle,))
        self.assertTrue(result)
        self.assertEqual(len(calls), 1)

    def test_traffic_neighbor_conflict_rejects_candidate(self):
        owner = make_owner(index=3, slot=7)
        traffic = bytearray(0x4F8)
        struct.pack_into('<I', traffic, 0, 4)
        struct.pack_into('<f', traffic, 0x48, 0.0)
        result, calls = probe(owner, traffic=(bytes(traffic),))
        self.assertFalse(result)
        self.assertEqual(calls, [])

    def test_surface_flags_and_vertical_normal_filter_match_native_gates(self):
        owner = make_owner()
        for flags, normal_y in ((0, 1.0), (0x0E, 1.0), (0x40, 1.0), (1, 0.79)):
            result, calls = probe(owner, sample=(True, flags, normal_y))
            self.assertFalse(result)
            self.assertEqual(len(calls), 1)
        result, calls = probe(owner, sample=(True, 1, 0.8))
        self.assertTrue(result)
        self.assertEqual(len(calls), 1)
        result, _ = probe(owner, sample=(True, 0x40, 0.0), surface_result=1)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
