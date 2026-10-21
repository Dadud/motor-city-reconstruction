"""Collision-offset search orchestration from the original 0x43ba40 routine."""
import struct

from .tire_response import f32
from .track_topology import (collision_fallback_offset, path_index_is_forward,
                             step_path_index)


def search_surface_correction(owner, track_index, *, path_rows, path_count,
                              attempts, wrapped_ordering, wrapped_index,
                              probe, apply_response, fallback_seed=None,
                              fallback_table=None,
                              special_probe=False, alternate_track_side=False,
                              response_mode=False, index_is_rejected=None):
    """Try the original ordered collision offsets around adjacent track rows.

    ``probe`` preserves the unresolved geometric/overlap child 0x43bd30;
    ``apply_response`` preserves 0x51e460. Supply either an explicit
    ``fallback_seed`` bridge or a bounded ``fallback_table`` for the native
    0x403070 lookup. A null table produces the original 0.0 fallback.
    """
    if not isinstance(owner, bytearray) or len(owner) < 0xDF8:
        raise ValueError('a mutable world-object image through +0xdf7 is required')
    if type(track_index) is not int or not 0 <= track_index < len(path_rows):
        raise ValueError('track index must select a supplied row')
    if type(path_count) is not int or path_count != len(path_rows) or path_count < 1:
        raise ValueError('path count must match the nonempty supplied row table')
    if type(attempts) is not int or attempts != path_count:
        raise ValueError('the observed global topology count must match the supplied path rows')
    if not callable(probe) or not callable(apply_response):
        raise ValueError('probe and response callbacks are required')
    if fallback_seed is not None and not callable(fallback_seed):
        raise ValueError('fallback seed must be callable when supplied')
    if fallback_seed is not None and fallback_table is not None:
        raise ValueError('supply either fallback_seed or fallback_table')
    if not wrapped_index and not callable(index_is_rejected):
        raise ValueError('clamped track stepping requires the native rejection predicate')

    side = track_index
    query_index = int.from_bytes(owner[0x370:0x374], 'little')
    response_flag = 2 if response_mode else 0
    calls = 0
    probe_generation = struct.unpack_from('<I', owner, 0x5b4)[0]
    struct.pack_into('<I', owner, 0x5b4, (probe_generation + 1) & 0xffffffff)

    def try_offset(index, offset):
        nonlocal calls
        offset = f32(offset)
        calls += 1
        if probe(owner, index, offset, 0, 0):
            apply_response(owner, index, offset, response_flag)
            return True
        return False

    if special_probe:
        row = path_rows[side]
        step = f32((row[1] if alternate_track_side else -row[0]) * f32(0.8))
        for multiplier in (1, 2):
            offset = f32(multiplier * step)
            if try_offset(side, offset):
                return side, offset, calls

    remaining = attempts
    while True:
        if remaining == 0:
            if fallback_seed is not None:
                seed = fallback_seed(track_index, response_mode)
            else:
                seed = collision_fallback_offset(
                    fallback_table, track_index, response_mode)
            offset = f32(seed)
            if try_offset(track_index, offset):
                return track_index, offset, calls
            return None, None, calls
        remaining -= 1

        row = path_rows[side]
        negative_spacing = f32(row[0])
        positive_spacing = f32(row[1])
        negative_count = int(row[2])
        positive_count = int(row[3])
        probe_count = max(negative_count, positive_count)
        for distance in range(max(0, probe_count)):
            if distance <= positive_count:
                offset = f32(positive_spacing * 0.5 + distance * positive_spacing)
                if try_offset(side, offset):
                    return side, offset, calls
            if distance <= negative_count:
                offset = f32(-(distance * negative_spacing) - negative_spacing * 0.5)
                if try_offset(side, offset):
                    return side, offset, calls

        is_forward = path_index_is_forward(
            path_count, query_index, track_index,
            wrapped_ordering=wrapped_ordering)
        step = -1 if is_forward else 1
        side = step_path_index(side, step, path_count, wrap_mode=wrapped_index,
                               index_is_rejected=index_is_rejected)
