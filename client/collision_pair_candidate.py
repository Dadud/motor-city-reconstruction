"""Candidate-record broadphase used by the dynamic pair pass at 0x45cf70."""
from dataclasses import dataclass
import math
import struct

from client.collision_pair_solver import resolve_collision_pair


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _get_f32(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


@dataclass(frozen=True)
class DynamicCandidateTable:
    records: bytes
    sources: bytes
    table_address: int
    source_address: int


def build_dynamic_candidate_table(sources, vertices_by_address, *,
                                  source_address, table_address):
    """Build the 0x427f50 dynamic-pair table from supplied 0x38-byte rows.

    ``vertices_by_address`` maps each source row's +0x28 pointer to packed
    XYZ float triples. Allocation and allocator-specific zeroing are outside
    this address-independent translation; the returned rows are byte-exact
    0x78-byte records, and ``sources`` includes the game's type/back-link
    mutations. Ineligible rows remain zero after the table's initial clear.
    """
    if len(sources) % 0x38:
        raise ValueError('source image must contain whole 0x38-byte rows')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in (source_address, table_address)):
        raise ValueError('source and table addresses must be uint32 values')
    count = len(sources) // 0x38
    if count > 0x7fffffff // 0x78:
        raise ValueError('candidate table size overflows the original allocation')
    mutated = bytearray(sources)
    table = bytearray(count * 0x78)
    for index in range(count):
        src = index * 0x38
        dst = index * 0x78
        old_link = struct.unpack_from('<I', mutated, src + 0x20)[0]
        struct.pack_into('<I', table, dst + 0x74, 0)
        point_count = struct.unpack_from('<I', mutated, src + 0x24)[0]
        kind = struct.unpack_from('<H', mutated, src + 2)[0] & 0xf
        if point_count == 0 or kind != 3:
            continue
        if point_count > 0x100000:
            raise ValueError('source vertex count exceeds bounded input limit')
        vertex_address = struct.unpack_from('<I', mutated, src + 0x28)[0]
        points = vertices_by_address.get(vertex_address)
        if points is None or len(points) != point_count * 12:
            raise ValueError('missing or incorrectly sized candidate vertex array')
        coordinates = struct.unpack('<' + 'f' * (point_count * 3), points)
        mins = [coordinates[axis] for axis in range(3)]
        maxs = list(mins)
        for point_index in range(1, point_count):
            for axis in range(3):
                value = coordinates[point_index * 3 + axis]
                if value < mins[axis]:
                    mins[axis] = value
                if maxs[axis] < value:
                    maxs[axis] = value
        center = [_f32(_f32(mins[axis] + maxs[axis]) * 0.5)
                  for axis in range(3)]
        extents = [_f32(_f32(maxs[axis] - mins[axis]) * 0.5)
                   for axis in range(3)]
        radius = _f32(math.sqrt(sum(value * value for value in extents)))
        struct.pack_into('<I', table, dst + 0x30,
                         struct.unpack_from('<I', mutated, src + 0x0c)[0])
        struct.pack_into('<I', table, dst + 0x74, old_link)
        struct.pack_into('<I', table, dst + 0x70,
                         struct.unpack_from('<I', mutated, src + 8)[0])
        struct.pack_into('<3f', table, dst + 0x4c, *center)
        struct.pack_into('<3f', table, dst + 0x3c, *extents)
        struct.pack_into('<f', table, dst + 0x48, radius)
        struct.pack_into('<H', mutated, src + 2, 5)
        struct.pack_into('<I', mutated, src + 0x20,
                         table_address + dst)
    return DynamicCandidateTable(bytes(table), bytes(mutated), table_address,
                                 source_address)


@dataclass(frozen=True)
class DynamicPairCandidate:
    eligible: bool
    center: tuple
    radius: float
    within_radius: bool


@dataclass(frozen=True)
class DynamicPairRetryResult:
    owner: object
    target: object
    attempts: int
    accepted_attempts: int
    response_due: bool


def dynamic_pair_candidate(owner, record):
    """Translate the record gates and transformed-center radius test.

    ``owner`` is the mutable body image. ``record`` is one 0x78-byte entry
    from the game's dynamic candidate table. This covers only the early pair
    broadphase; record setup and the pair resolver remain separate stages.
    """
    if len(owner) < 0xdc or len(record) < 0x78:
        raise ValueError('owner and candidate images must cover their source fields')
    eligible = (_get_f32(record, 0x74) != 0.0 and
                _get_f32(record, 0x30) != 0.0)
    matrix = tuple(_get_f32(record, 0x0c + 4 * i) for i in range(9))
    local = tuple(_get_f32(record, 0x4c + 4 * i) for i in range(3))
    origin = tuple(_get_f32(record, 4 * i) for i in range(3))
    center = (
        _f32(_f32(_f32(_f32(local[2] * matrix[6]) +
                       _f32(local[1] * matrix[3])) +
                   _f32(local[0] * matrix[0])) + origin[0]),
        _f32(_f32(_f32(_f32(local[2] * matrix[7]) +
                       _f32(local[1] * matrix[4])) +
                   _f32(local[0] * matrix[1])) + origin[1]),
        _f32(_f32(_f32(_f32(local[2] * matrix[8]) +
                       _f32(local[1] * matrix[5])) +
                   _f32(local[0] * matrix[2])) + origin[2]))
    radius = _f32(_get_f32(owner, 0xd8) + _get_f32(record, 0x48))
    delta = tuple(_f32(_get_f32(owner, offset) - center[axis])
                  for axis, offset in enumerate((8, 0x0c, 0x10)))
    distance_squared = _f32(_f32(_f32(delta[0] * delta[0]) +
                                 _f32(delta[1] * delta[1])) +
                             _f32(delta[2] * delta[2]))
    within = eligible and distance_squared <= _f32(radius * radius)
    return DynamicPairCandidate(eligible, center, radius, within)


def resolve_dynamic_pair_retries(owner, target, max_attempts=33):
    """Translate the ``0x45cf70`` retry loop around the ``0x45af30`` solver.

    Each accepted solver call updates both body states before the next attempt.
    A rejection exits immediately; any prior acceptance schedules exactly one
    pair-response call in the original caller. The native loop permits 33 calls.
    """
    if type(max_attempts) is not int or not 1 <= max_attempts <= 33:
        raise ValueError('dynamic-pair attempts must be between 1 and 33')
    accepted = 0
    attempts = 0
    current_owner, current_target = owner, target
    while attempts < max_attempts:
        result = resolve_collision_pair(current_owner, current_target)
        attempts += 1
        current_owner, current_target = result.owner, result.target
        if not result.collided:
            break
        accepted += 1
    return DynamicPairRetryResult(current_owner, current_target, attempts,
                                  accepted, accepted != 0)
