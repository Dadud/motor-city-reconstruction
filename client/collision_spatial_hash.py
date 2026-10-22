"""Spatial-hash sphere gates used by the active-object builder at 0x426770."""
import struct


def _get_u32(image, offset):
    return struct.unpack_from('<I', image, offset)[0]


def _sphere_overlap_fields(owner, candidate, owner_position, candidate_position,
                           owner_radius, candidate_radius):
    distance_squared = 0.0
    for axis in range(3):
        delta = _f32(_get_f32(candidate, candidate_position + axis * 4) -
                     _get_f32(owner, owner_position + axis * 4))
        distance_squared = _f32(distance_squared + _f32(delta * delta))
    radius = _f32(_get_f32(candidate, candidate_radius) +
                  _get_f32(owner, owner_radius))
    return _f32(radius * radius) >= distance_squared


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _get_f32(image, offset):
    return struct.unpack_from('<f', image, offset)[0]


def sphere_overlap(owner, candidate):
    """Return the inclusive center/radius test implemented at 0x426af0.

    Both inputs are body images: XYZ center at ``+8`` and radius at ``+0xd8``.
    The function preserves single-precision intermediate rounding.
    """
    if len(owner) < 0xdc or len(candidate) < 0xdc:
        raise ValueError('sphere bodies must include center and radius fields')
    return _sphere_overlap_fields(owner, candidate, 8, 8, 0xd8, 0xd8)


def mark_sphere_neighbors(owner, candidates):
    """Apply the 0x426b40 linked-list update to supplied cell members.

    The owner is skipped by identity. Only candidates whose active byte at
    ``+4`` is zero are tested; overlapping candidates have that byte set to 1.
    Candidate ordering matches traversal order but does not affect the writes.
    """
    if len(owner) < 0xdc:
        raise ValueError('owner body must include center and radius fields')
    marked = 0
    for candidate in candidates:
        if not isinstance(candidate, bytearray) or len(candidate) < 0x4f8:
            raise ValueError('cell candidates must be mutable 0x4f8-byte body images')
        if candidate is owner or candidate[4] != 0:
            continue
        if sphere_overlap(owner, candidate):
            candidate[4] = 1
            marked += 1
    return marked


def mark_spatial_hash_neighbors(bodies, hash_cells, neighbor_cells):
    """Translate the nine-cell marking pass at 0x426bc0.

    ``bodies`` is the original body-array order; ``hash_cells`` maps a cell
    index to its linked-list order; ``neighbor_cells`` maps each active body's
    cell index to the eight signed neighbor slots. Missing/negative slots are
    skipped exactly as the native ``if (index >= 0)`` gate does.
    """
    bodies = tuple(bodies)
    if any(not isinstance(body, bytearray) or len(body) < 0x4f8
           for body in bodies):
        raise ValueError('spatial-hash bodies must be mutable 0x4f8-byte images')
    marked = 0
    for owner in bodies:
        if owner[4] == 0:
            continue
        cell = _get_u32(owner, 0x374)
        if cell >= 300:
            raise ValueError('body hash cell is outside the 300-entry head table')
        neighbors = neighbor_cells.get(cell)
        if neighbors is None or len(neighbors) != 8:
            raise ValueError('each active body needs eight observed neighbor slots')
        for group in (cell, *neighbors):
            if type(group) is not int or group < -1 or group >= 300:
                raise ValueError('neighbor cells must be -1 or a valid hash index')
            if group >= 0:
                marked += mark_sphere_neighbors(owner, hash_cells.get(group, ()))
    return marked


def rebuild_collision_spatial_flags(bodies, active_roster, neighbor_cells,
                                    dynamic_records=(), *, body_addresses):
    """Translate the active/hash/dynamic candidate pass in 0x426770.

    The caller supplies the 0x4f8-byte body array, its active roster, the eight
    signed neighbor slots per cell and the initialized 0x78-byte dynamic rows.
    The routine mutates active flags, per-body hash links, and inactive body's
    six cached motion fields just like the original. Hash-chain insertion is
    head-first in body-array order.
    """
    bodies = tuple(bodies)
    body_addresses = tuple(body_addresses)
    active_roster = tuple(active_roster)
    dynamic_records = tuple(dynamic_records)
    if any(not isinstance(body, bytearray) or len(body) < 0x4f8 for body in bodies):
        raise ValueError('body array entries must be mutable 0x4f8-byte images')
    if (len(body_addresses) != len(bodies) or
            any(type(address) is not int or not 0 < address <= 0xffffffff
                for address in body_addresses) or
            len(set(body_addresses)) != len(body_addresses)):
        raise ValueError('one unique non-null uint32 address is required per body')
    if len({id(body) for body in bodies}) != len(bodies):
        raise ValueError('body array cannot contain duplicate mutable images')
    if any(not isinstance(body, bytearray) or len(body) < 0x4f8
           for body in active_roster):
        raise ValueError('active roster entries must be mutable 0x4f8-byte images')
    if any(len(record) < 0x78 for record in dynamic_records):
        raise ValueError('dynamic candidate records must cover 0x78 bytes')

    for body in bodies:
        if body[4] == 0:
            continue
        if _get_f32(body, 0x6c) != 0.0:
            body[4] = 0
        low_motion = (_get_f32(body, 0x3b4) < _f32(.15) and
                      _get_f32(body, 0x18) <= _f32(.30625) and
                      abs(_get_f32(body, 0x3c)) < _f32(.05) and
                      abs(_get_f32(body, 0x38)) < _f32(.02) and
                      abs(_get_f32(body, 0x40)) < _f32(.02))
        if (_i16(body, 0x3bc) == 0 and low_motion and
                _get_f32(body, 0x350) < _get_f32(body, 0xd8)):
            body[4] = 0

    hash_cells = {}
    address_by_identity = {id(body): address
                           for body, address in zip(bodies, body_addresses)}
    for body in bodies:
        cell = _get_u32(body, 0x374)
        if cell >= 300:
            raise ValueError('body hash cell is outside the 300-entry head table')
        previous = hash_cells.setdefault(cell, [])
        struct.pack_into('<I', body, 0x4f4,
                         address_by_identity[id(previous[0])] if previous else 0)
        previous.insert(0, body)

    def mark_group(owner, cell):
        if type(cell) is not int or not 0 <= cell < 300:
            raise ValueError('queried group index is outside the hash table')
        return mark_sphere_neighbors(owner, hash_cells.get(cell, ()))

    for owner in active_roster:
        if owner[4] == 0:
            continue
        cell = _get_u32(owner, 0x374)
        for candidate in hash_cells.get(cell, ()):
            if candidate is owner or candidate[4] != 0:
                continue
            if sphere_overlap(owner, candidate):
                candidate[4] = 1
        slots = neighbor_cells.get(cell)
        if slots is None or len(slots) != 8:
            raise ValueError('each active roster body needs eight neighbor slots')
        for group in slots:
            if group >= 0:
                mark_group(owner, group)

    for record in dynamic_records:
        if (_get_u32(record, 0x74) == 0 or
                _get_u32(record, 0x30) == 0):
            continue
        cell = _get_u32(record, 0x38)
        if cell >= 300:
            raise ValueError('dynamic candidate cell is outside the hash table')
        slots = neighbor_cells.get(cell)
        if slots is None or len(slots) != 8:
            raise ValueError('each dynamic candidate needs eight neighbor slots')
        for group in (cell, *slots):
            if group < 0:
                continue
            for candidate in hash_cells.get(group, ()):
                if candidate[4] != 0:
                    continue
                if _sphere_overlap_fields(candidate, record, 8, 0, 0xd8, 0x48):
                    candidate[4] = 1
    mark_spatial_hash_neighbors(bodies, hash_cells, neighbor_cells)

    for body in bodies:
        if body[4] == 0:
            for offset in (0x14, 0x18, 0x1c, 0x38, 0x3c, 0x40):
                struct.pack_into('<f', body, offset, 0.0)
    return hash_cells


def _i16(image, offset):
    return struct.unpack_from('<h', image, offset)[0]
