"""Single-body vertex-to-plane response called by object-pair dispatch."""
from dataclasses import dataclass
import math
import struct

from .collision_impulse import CollisionInertia
from .collision_pair_response import (CollisionImpactBody,
                                      resolve_surface_impulse)
from .collision_world_response import extract_world_contact_points
from .geometry_transform import add_vector_to_points, transform_vertices
from .tire_response import f32


@dataclass(frozen=True)
class PairSurfaceResult:
    body_image: bytes
    collided: bool
    selected_vertex: int | None
    contact_point: tuple | None
    penetration: float
    impulse_samples: int


def _dot(a, b):
    return (float(a[0]) * b[0] + float(a[1]) * b[1]) + float(a[2]) * b[2]


def _body_from_image(image, address):
    return CollisionImpactBody(
        address, struct.unpack_from('<3f', image, 8),
        struct.unpack_from('<3f', image, 0x14),
        struct.unpack_from('<3f', image, 0x38),
        struct.unpack_from('<3f', image, 0x5c),
        # The target's inverse inertia tensor is the matrix consumed by the
        # support impulse helper. The companion +0x78 matrix is stored too.
        CollisionInertia(
            struct.unpack_from('<f', image, 0x54)[0],
            struct.unpack_from('<3f', image, 0x2fc),
            struct.unpack_from('<9f', image, 0x9c),
            struct.unpack_from('<9f', image, 0x78)),
        struct.unpack_from('<f', image, 0x50)[0], mode=image[5],
        response_coefficient=struct.unpack_from('<f', image, 0x68)[0],
        gate=struct.unpack_from('<f', image, 0x6c)[0],
        peer_gate=struct.unpack_from('<f', image, 0x3c0)[0],
        contact_record=bytes(image[:0x400]),
        embedded_contact_pointer=struct.unpack_from('<I', image, 0x404)[0])


def resolve_pair_surface(owner_image, owner_address, normal, plane_point,
                         maximum_distance, threshold_coefficient,
                         sliding_coefficient, maximum_vertex_height):
    """Translate original ``0x459b90`` for an explicit plane and body image.

    The selected world point minimizes signed distance to ``plane_point``
    among transformed vertices below the height limit and moving inward
    relative to the supplied normal. A penetration correction translates both
    the body and its cached 22-point world geometry before impulse resolution.
    """
    image = bytes(owner_image)
    if len(image) < 0x408:
        raise ValueError('owner image must cover the 0x408-byte body record')
    if type(owner_address) is not int or not 0 <= owner_address <= 0xffffffff:
        raise ValueError('owner address must be a uint32')
    if len(normal) != 3 or len(plane_point) != 3:
        raise ValueError('plane normal and point must be 3D')
    n = tuple(f32(value) for value in normal)
    plane = tuple(f32(value) for value in plane_point)
    maximum_distance = f32(maximum_distance)
    maximum_vertex_height = f32(maximum_vertex_height)
    threshold_coefficient = f32(threshold_coefficient)
    sliding_coefficient = f32(sliding_coefficient)
    if not all(math.isfinite(value) for value in
               (*n, *plane, maximum_distance, maximum_vertex_height,
                threshold_coefficient, sliding_coefficient)):
        raise ValueError('pair-surface inputs must be finite')

    points = extract_world_contact_points(image)
    position = struct.unpack_from('<3f', image, 8)
    matrix = struct.unpack_from('<9f', image, 0x78)
    world_points = transform_vertices(points.vertices, matrix, position,
                                      count=points.count)
    closest_distance = maximum_distance
    closest_index = None
    closest_point = None
    for index in range(points.count):
        offset = index * 3
        point = world_points[offset:offset + 3]
        if point[1] <= maximum_vertex_height:
            distance = _dot(tuple(f32(point[i] - plane[i]) for i in range(3)), n)
            inward = _dot(tuple(f32(point[i] - position[i]) for i in range(3)), n)
            if distance < closest_distance and inward < 0.0:
                closest_distance = distance
                closest_index = index
                closest_point = tuple(point)

    if closest_index is None:
        return PairSurfaceResult(image, False, None, None, 0.0, 0)

    updated = bytearray(image)
    relative = tuple(f32(closest_point[i] - plane[i]) for i in range(3))
    plane_projection = _dot(relative, n)
    if plane_projection < 0.0:
        penetration = f32(-plane_projection)
        displacement = tuple(f32(n[i] * penetration) for i in range(3))
        position = tuple(f32(position[i] + displacement[i]) for i in range(3))
        closest_point = tuple(f32(closest_point[i] + displacement[i])
                              for i in range(3))
        cached = struct.unpack_from('<66f', updated, 0x1e8)
        cached = add_vector_to_points(cached, displacement, count=22)
        struct.pack_into('<66f', updated, 0x1e8, *cached)
        struct.pack_into('<3f', updated, 8, *position)
    else:
        penetration = 0.0

    body = _body_from_image(updated, owner_address)
    response = resolve_surface_impulse(body, closest_point, n,
                                       threshold_coefficient,
                                       sliding_coefficient)
    if response.collided:
        updated[:0x400] = response.body.contact_record
        struct.pack_into('<3f', updated, 0x14, *response.body.linear_velocity)
        struct.pack_into('<3f', updated, 0x38,
                         *response.body.angular_turn_velocity)
    return PairSurfaceResult(bytes(updated), response.collided,
                             closest_index, tuple(closest_point), penetration,
                             response.samples)
