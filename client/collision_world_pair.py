"""Sample-trigger decision-minus-one pair response from ``0x45d1f0``."""
from dataclasses import dataclass
import math
import struct

from client.body_constructor import construct_body
from client.collision_impulse import CollisionInertia
from client.collision_pair_response import (CollisionImpactBody,
                                            resolve_pair_impulse)
from client.tire_response import f32


@dataclass(frozen=True)
class WorldPairResponseResult:
    body_image: bytes
    temporary_body_image: bytes
    collided: bool
    contact_point: tuple[float, float, float]
    normal: tuple[float, float, float]
    impulse_samples: int


def _impact_body(image, address):
    return CollisionImpactBody(
        address, struct.unpack_from('<3f', image, 8),
        struct.unpack_from('<3f', image, 0x14),
        struct.unpack_from('<3f', image, 0x38),
        struct.unpack_from('<3f', image, 0x5c),
        CollisionInertia(
            struct.unpack_from('<f', image, 0x54)[0],
            struct.unpack_from('<3f', image, 0x2fc),
            struct.unpack_from('<9f', image, 0x78),
            struct.unpack_from('<9f', image, 0x9c)),
        struct.unpack_from('<f', image, 0x50)[0], mode=image[5],
        response_coefficient=struct.unpack_from('<f', image, 0x68)[0],
        gate=struct.unpack_from('<f', image, 0x6c)[0],
        peer_gate=struct.unpack_from('<f', image, 0x3c0)[0],
        contact_record=bytes(image[:0x400]),
        embedded_contact_pointer=struct.unpack_from('<I', image, 0x404)[0])


def resolve_world_decision_minus_one(owner_image, sample_position,
                                     vertical_value, type_code,
                                     owner_address, temporary_body_address,
                                     threshold_coefficient,
                                     sliding_coefficient):
    """Build the type-2 proxy, call the pair solver, and apply its cache writes.

    The temporary body's address is caller-supplied because the original keeps
    this 0x418-byte proxy in the ``0x45d1f0`` stack frame. Pair-response
    coefficients are also inputs: the original reads them from shared globals.
    """
    image = bytes(owner_image)
    position = tuple(f32(value) for value in sample_position)
    vertical_value = f32(vertical_value)
    if len(image) < 0x408 or len(position) != 3:
        raise ValueError('owner image must span 0x408 bytes and sample position be 3D')
    for value, label in ((owner_address, 'owner'),
                         (temporary_body_address, 'temporary body'),
                         (type_code, 'type code')):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError(f'{label} address/code must be a uint32')
    if abs(vertical_value) > 1e3:
        raise ValueError('proxy half extent is outside the supported source range')
    if not all(math.isfinite(value) for value in (*position,
                                                   threshold_coefficient,
                                                   sliding_coefficient)):
        raise ValueError('pair-response coordinates and coefficients must be finite')

    proxy = bytearray(construct_body(bytes(0x2000), 0xfffffffd, 25.,
                                     (vertical_value, 3., vertical_value), 0, 2))
    struct.pack_into('<3f', proxy, 8, *position)
    owner_position = struct.unpack_from('<3f', image, 8)
    contact = (position[0], owner_position[1], position[2])
    delta_x = f32(owner_position[0] - position[0])
    delta_z = f32(owner_position[2] - position[2])
    length_squared = (delta_z * delta_z + 0.0) + delta_x * delta_x
    if length_squared == 0.0:
        return WorldPairResponseResult(image, bytes(proxy), False, contact,
                                       (0., 0., 0.), 0)
    if vertical_value == 0.0:
        raise ValueError('zero-sized proxy inertia remains outside the verified pair domain')
    length = math.sqrt(length_squared)
    reciprocal = 1.0 / length
    normal = (f32(delta_x * reciprocal), 0., f32(delta_z * reciprocal))
    pair = resolve_pair_impulse(
        _impact_body(image, owner_address),
        _impact_body(proxy, temporary_body_address), contact, normal,
        f32(threshold_coefficient), f32(sliding_coefficient))

    updated = bytearray(image)
    updated[:0x400] = pair.owner.contact_record
    struct.pack_into('<3f', updated, 8, *pair.owner.position)
    struct.pack_into('<3f', updated, 0x14, *pair.owner.linear_velocity)
    struct.pack_into('<3f', updated, 0x38, *pair.owner.angular_turn_velocity)
    if pair.collided:
        struct.pack_into('<I', updated, 0x3c4, 0)
        struct.pack_into('<I', updated, 0x3f4, 5)
        struct.pack_into('<I', updated, 0x3f8, type_code)
        counter = struct.unpack_from('<f', image, 0x3b4)[0]
        mass = struct.unpack_from('<f', image, 0x50)[0]
        magnitude = f32((counter * 0.14913242 + 5.0) * mass)
        struct.pack_into('<f', updated, 0x3c8, magnitude)
    return WorldPairResponseResult(bytes(updated), bytes(proxy), pair.collided,
                                   contact, normal, pair.samples)
