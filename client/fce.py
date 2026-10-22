"""Decode the observed 0x101014/0x101015 FCE geometry layout.

Format corroboration: LibOpenNFS NFS4 FceFile.h/.cpp (MIT), and local MCO files.
New implementation. Damaged geometry, textures and animation are not decoded yet.
"""
from dataclasses import dataclass
import math
import struct

HEADER = 0x2038


@dataclass(frozen=True)
class Triangle:
    indices: tuple[int, int, int]
    uv: tuple[float, ...]
    texture_page: int
    flags: int


@dataclass(frozen=True)
class Part:
    name: str
    origin: tuple[float, float, float]
    vertices: tuple[tuple[float, float, float], ...]
    normals: tuple[tuple[float, float, float], ...]
    triangles: tuple[Triangle, ...]
    vertex_colors: tuple[int, ...] = ()


@dataclass(frozen=True)
class Model:
    parts: tuple[Part, ...]
    version: int
    warnings: tuple[str, ...] = ()

    @property
    def triangle_count(self):
        return sum(len(p.triangles) for p in self.parts)


def decode(data: bytes) -> Model:
    if len(data) < HEADER:
        raise ValueError('FCE header truncated')
    version, _, triangles, vertices = struct.unpack_from('<4I', data)
    if version not in (0x101014, 0x101015):
        raise ValueError(f'unsupported FCE version 0x{version:x}')
    num_parts = struct.unpack_from('<I', data, 0x11c)[0]
    if not 1 <= num_parts <= 64:
        raise ValueError('invalid FCE part count')
    if vertices > 1_000_000 or triangles > 2_000_000:
        raise ValueError('FCE exceeds geometry budget')
    offsets = struct.unpack_from('<3I', data, 0x14)
    ranges = []
    for offset, count, stride in zip(offsets, (vertices, vertices, triangles), (12, 12, 56)):
        start, end = HEADER + offset, HEADER + offset + count * stride
        if end > len(data):
            raise ValueError('FCE table extends past EOF')
        if count:
            ranges.append((start, end))
    ordered = sorted(ranges)
    if any(b[0] < a[1] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('FCE geometry tables overlap')

    def floats(offset, count):
        values = struct.unpack_from(f'<{count}f', data, offset)
        if any(not math.isfinite(v) for v in values):
            raise ValueError('non-finite geometry')
        return values

    parts, warnings = [], []
    vertex_ranges, triangle_ranges = [], []
    for index in range(num_parts):
        first_vertex = struct.unpack_from('<I', data, 0x420 + index * 4)[0]
        vertex_count = struct.unpack_from('<I', data, 0x520 + index * 4)[0]
        first_triangle = struct.unpack_from('<I', data, 0x620 + index * 4)[0]
        triangle_count = struct.unpack_from('<I', data, 0x720 + index * 4)[0]
        if first_vertex + vertex_count > vertices or first_triangle + triangle_count > triangles:
            raise ValueError('FCE part outside global table')
        if vertex_count:
            vertex_ranges.append((first_vertex, first_vertex + vertex_count))
        if triangle_count:
            triangle_ranges.append((first_triangle, first_triangle + triangle_count))
        origin = floats(0x120 + index * 12, 3)
        name_bytes = data[0xe28 + index * 64:0xe28 + (index + 1) * 64]
        terminator = name_bytes.find(b'\0')
        if terminator < 0:
            raise ValueError('unterminated FCE part name')
        name = name_bytes[:terminator].decode('latin-1')
        positions = tuple(floats(HEADER + offsets[0] + (first_vertex + v) * 12, 3)
                          for v in range(vertex_count))
        normals = [struct.unpack_from('<3f', data, HEADER + offsets[1] + (first_vertex + v) * 12)
                   for v in range(vertex_count)]
        faces = []
        for triangle in range(first_triangle, first_triangle + triangle_count):
            location = HEADER + offsets[2] + triangle * 56
            page, a, b, c = struct.unpack_from('<4I', data, location)
            if max(a, b, c) >= vertex_count:
                raise ValueError('FCE triangle index outside part')
            flags = struct.unpack_from('<I', data, location + 28)[0]
            uv = floats(location + 32, 6)
            faces.append(Triangle((a, b, c), uv, page, flags))
        invalid = [v for v, normal in enumerate(normals) if any(not math.isfinite(x) for x in normal)]
        if invalid:
            # Two installed cars contain NaN normals. Rebuild those normals from
            # adjacent face geometry, preserving positions and reporting the repair.
            sums = [[0.0, 0.0, 0.0] for _ in positions]
            for face in faces:
                a, b, c = (positions[v] for v in face.indices)
                ab, ac = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
                n = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
                for v in face.indices:
                    for i in range(3):
                        sums[v][i] += n[i]
            for v in invalid:
                length = math.sqrt(sum(x*x for x in sums[v]))
                normals[v] = tuple(x/length for x in sums[v]) if length else (0.0, 1.0, 0.0)
            warnings.append(f'{name}: rebuilt {len(invalid)} non-finite normals')
        parts.append(Part(name, origin, positions, tuple(normals), tuple(faces)))
    for ranges in (vertex_ranges, triangle_ranges):
        ranges.sort()
        if any(b[0] < a[1] for a, b in zip(ranges, ranges[1:])):
            raise ValueError('overlapping FCE parts')
    return Model(tuple(parts), version, tuple(warnings))
