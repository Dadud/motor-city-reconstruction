"""Four-edge candidate contact selection used inside original 0x45c3e0."""
from dataclasses import dataclass
import math
import struct


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


@dataclass(frozen=True)
class CollisionEdgeRecord:
    """One contact polygon record consumed by 0x42d900/0x45c870.

    The original record stores an identity/pointer at +0x0c, a four-byte
    per-edge weight array, and four pointers to world-space vertices. Keeping
    these fields explicit avoids claiming the enclosing 0x44-byte record is
    fully identified.
    """
    identity: int
    vertices: tuple
    edge_weights: bytes

    def __post_init__(self):
        if type(self.identity) is not int or not 0 <= self.identity <= 0xffffffff:
            raise ValueError('edge-record identity must be a uint32')
        if len(self.vertices) != 4 or any(len(point) != 3 for point in self.vertices):
            raise ValueError('four 3D edge vertices are required')
        if len(self.edge_weights) != 4:
            raise ValueError('four edge weights are required')
        values = tuple(value for point in self.vertices for value in point)
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError('edge vertices must be finite')


@dataclass(frozen=True)
class EdgeContactResult:
    accepted: bool
    edge_mask: int
    normal: tuple
    point: tuple
    vertical_value: float


def edge_crossing_mask(point, polygon, comparison_polygon):
    """Translate original 0x42d900's four signed XZ edge tests."""
    if not isinstance(polygon, CollisionEdgeRecord) or not isinstance(
            comparison_polygon, CollisionEdgeRecord):
        raise ValueError('two collision edge records are required')
    if len(point) != 3 or not all(math.isfinite(float(value)) for value in point):
        raise ValueError('a finite 3D query point is required')
    if polygon.identity == comparison_polygon.identity:
        return 0

    x, _y, z = (_f32(value) for value in point)
    vertices = tuple(tuple(_f32(value) for value in vertex)
                     for vertex in polygon.vertices)
    mask = 0
    limits = (0.0, 1.5, 0.0, 1.5)
    for edge, limit in enumerate(limits):
        start, end = vertices[edge], vertices[(edge + 1) & 3]
        signed_area = ((z - start[2]) * (end[0] - start[0]) -
                       (x - start[0]) * (end[2] - start[2]))
        if signed_area <= limit:
            mask |= 1 << edge
    return mask


def resolve_edge_contact(point, polygon, comparison_polygon):
    """Translate original 0x45c870's edge-mask normal and vertex selection."""
    mask = edge_crossing_mask(point, polygon, comparison_polygon)
    if mask == 0:
        return EdgeContactResult(False, 0, (0.0, 0.0, 0.0),
                                 (0.0, 0.0, 0.0), 0.0)
    vertices = tuple(tuple(_f32(value) for value in vertex)
                     for vertex in polygon.vertices)
    weights = tuple(polygon.edge_weights)
    normal_sum = [0.0, 0.0, 0.0]
    height_sum = 0.0
    count = 0
    edge_data = ((0x1, 0, 0, 0, .5), (0x2, 1, 1, 2, .25),
                 (0x4, 2, 2, 3, .25), (0x8, 3, 3, 0, .25))
    for bit, weight_index, start_index, height_index, weight_scale in edge_data:
        if not mask & bit or weights[weight_index] == 0:
            continue
        start = vertices[start_index]
        end = vertices[(start_index + 1) & 3]
        dx = _f32(end[0] - start[0])
        dz = _f32(start[2] - end[2])
        length_squared = (dx * dx + 0.0) + dz * dz
        normal = (dx, 0.0, dz)
        if length_squared != 0.0:
            inverse_length = 1.0 / math.sqrt(length_squared)
            dx = _f32(dx * inverse_length)
            dz = _f32(dz * inverse_length)
        normal_sum[0] = _f32(normal_sum[0] + dz)
        normal_sum[1] = _f32(normal_sum[1] + 0.0)
        normal_sum[2] = _f32(normal_sum[2] + dx)
        height_sum = _f32(height_sum +
                          _f32(weights[weight_index] * weight_scale +
                               vertices[height_index][1]))
        count += 1

    if mask & 1:
        selected = 1 if mask & 2 else 0
    elif mask & 4:
        selected = 2 if mask & 2 else 3
    else:
        selected = 1 if mask & 2 else 0
    selected_point = vertices[selected]

    if count == 0:
        return EdgeContactResult(False, mask, tuple(normal_sum), selected_point, 0.0)
    reciprocal = 1.0 / count
    normal_sum = [_f32(component * reciprocal) for component in normal_sum]
    squared = ((normal_sum[2] * normal_sum[2] +
                normal_sum[1] * normal_sum[1]) +
               normal_sum[0] * normal_sum[0])
    if squared != 0.0:
        inverse_length = 1.0 / math.sqrt(squared)
        normal_sum = [_f32(component * inverse_length) for component in normal_sum]
    accepted = squared != 0.0
    return EdgeContactResult(accepted, mask, tuple(normal_sum), selected_point,
                             _f32(height_sum / count))
