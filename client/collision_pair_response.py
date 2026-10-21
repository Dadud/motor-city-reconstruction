"""Pairwise impulse accumulation recovered from original 0x458530."""
from dataclasses import dataclass, replace
import math

from client.collision_impulse import CollisionInertia, impulse_motion
from client.collision_response import tangential_response
from client.tire_response import f32


@dataclass(frozen=True)
class CollisionImpactBody:
    address: int
    position: tuple
    linear_velocity: tuple
    angular_turn_velocity: tuple
    center_of_mass_local: tuple
    inertia: CollisionInertia
    mass: float
    mode: int = 0
    response_coefficient: float = 0.0
    gate: float = 0.0
    peer_gate: float = 0.0
    contact_record: bytes = bytes(0x400)


@dataclass(frozen=True)
class CollisionImpactResult:
    collided: bool
    owner: CollisionImpactBody
    target: CollisionImpactBody
    samples: int
    impact_status: int
    effective_mass: float


def _v3(values):
    if len(values) != 3:
        raise ValueError('collision vectors must contain three components')
    return tuple(f32(value) for value in values)


def _add(a, b):
    return tuple(f32(a[i] + b[i]) for i in range(3))


def _sub(a, b):
    return tuple(f32(a[i] - b[i]) for i in range(3))


def _scale(a, scalar):
    scalar = f32(scalar)
    return tuple(f32(value * scalar) for value in a)


def _dot(a, b):
    return f32((a[0] * b[0] + a[1] * b[1]) + a[2] * b[2])


def _cross(a, b):
    return (f32(a[1] * b[2] - a[2] * b[1]),
            f32(a[2] * b[0] - a[0] * b[2]),
            f32(a[0] * b[1] - a[1] * b[0]))


def _transform(vector, matrix):
    return tuple(f32((vector[0] * matrix[i] + vector[1] * matrix[i + 3]) +
                     vector[2] * matrix[i + 6]) for i in range(3))


def _response_modes(owner, target):
    owner_gate = bool(owner.mode) and not bool(target.mode)
    target_gate = bool(target.mode) and not bool(owner.mode)
    if target.peer_gate < owner.gate:
        owner_gate = True
    if owner.peer_gate < target.gate:
        target_gate = True
    if owner_gate and target_gate:
        owner_gate = target_gate = False
    return not owner_gate, not target_gate


def _lever(body, contact):
    center_offset = _transform(body.center_of_mass_local, body.inertia.body_to_world)
    # Preserve the source's left-associated contact - position - COM offset.
    lever = _sub(_sub(contact, body.position), center_offset)
    length = math.sqrt(sum(float(value) * value for value in lever))
    radial = tuple(f32(value / length) for value in lever) if length else (0., 0., 0.)
    return lever, radial


def _write_contact(record, other, point, normal_impulse, tangential_impulse,
                   status, approach, effective_mass):
    data = bytearray(record)
    if len(data) < 0x400:
        raise ValueError('collision contact record must span at least 0x400 bytes')
    import struct
    struct.pack_into('<I', data, 0x3c4, other)
    struct.pack_into('<f', data, 0x3c8, abs(approach))
    struct.pack_into('<3f', data, 0x3cc, *normal_impulse)
    struct.pack_into('<3f', data, 0x3d8, *tangential_impulse)
    struct.pack_into('<I', data, 0x3e4, status)
    struct.pack_into('<3f', data, 0x3e8, *point)
    struct.pack_into('<II', data, 0x3f4, 4, 6)
    struct.pack_into('<f', data, 0x3fc, effective_mass)
    return bytes(data)


def resolve_pair_impulse(owner, target, contact_point, normal,
                         threshold_coefficient, sliding_coefficient,
                         max_samples=32):
    """Translate sampled impact response and reciprocal contact records in 0x458530."""
    if not isinstance(owner, CollisionImpactBody) or not isinstance(target, CollisionImpactBody):
        raise ValueError('two collision impact bodies are required')
    if type(max_samples) is not int or not 1 <= max_samples <= 32:
        raise ValueError('sample limit must be between 1 and 32')
    contact, normal = _v3(contact_point), _v3(normal)
    for body in (owner, target):
        if len(body.contact_record) < 0x400 or body.address < 0 or body.address > 0xffffffff:
            raise ValueError('collision body address and contact image are invalid')

    lever_a, radial_a = _lever(owner, contact)
    lever_b, radial_b = _lever(target, contact)
    owner_movable, target_movable = _response_modes(owner, target)
    if owner_movable and not target_movable:
        effective_mass = f32(owner.mass)
    elif not owner_movable and target_movable:
        effective_mass = f32(target.mass)
    else:
        effective_mass = f32((f32(owner.mass * target.mass)) /
                             f32(owner.mass + target.mass))

    response_weight = f32(f32(owner.response_coefficient + target.response_coefficient) * .5 + 1.)
    linear_a = [0., 0., 0.]
    angular_a = [0., 0., 0.]
    linear_b = [0., 0., 0.]
    angular_b = [0., 0., 0.]
    current_linear_a, current_linear_b = owner.linear_velocity, target.linear_velocity
    current_angular_a = tuple(f32(value * 6.2831855) for value in owner.angular_turn_velocity)
    current_angular_b = tuple(f32(value * 6.2831855) for value in target.angular_turn_velocity)
    record_a, record_b = owner.contact_record, target.contact_record
    samples = 0
    status = 0
    for step in range(max_samples):
        time = f32(step * .03125)
        # Sampled point velocity uses the current full angular rate. The sample
        # fraction scales the impulses below, not this angular contribution.
        omega_a, omega_b = current_angular_a, current_angular_b
        velocity_a = _add(current_linear_a, _cross(omega_a, lever_a))
        velocity_b = _add(current_linear_b, _cross(omega_b, lever_b))
        relative = _scale(_sub(velocity_a, velocity_b), effective_mass)
        approach = _dot(relative, normal)
        if approach >= 0:
            break

        magnitude = f32(-approach)
        normal_impulse = _scale(normal, magnitude)
        response = tangential_response(relative, normal,
                                       threshold_coefficient, sliding_coefficient)
        tangential_impulse = response.vector
        status = response.status
        if step == 0:
            record_a = _write_contact(record_a, target.address, contact,
                                      normal_impulse, tangential_impulse,
                                      status, approach, effective_mass)
            record_b = _write_contact(record_b, owner.address, contact,
                                      _scale(normal_impulse, -1),
                                      _scale(tangential_impulse, -1),
                                      status, approach, effective_mass)

        normal_at_time = _scale(normal_impulse, time)
        tangential_at_time = _scale(tangential_impulse, time)
        if owner_movable:
            normal_motion = impulse_motion(owner.inertia, normal_at_time, lever_a, radial_a)
            tangent_motion = impulse_motion(owner.inertia, tangential_at_time, lever_a, radial_a)
            current_linear_a = _add(_add(current_linear_a, tangent_motion.linear),
                                    normal_motion.linear)
            current_angular_a = _add(_add(current_angular_a, tangent_motion.angular),
                                     normal_motion.angular)
            for i in range(3):
                linear_a[i] = f32(f32(normal_motion.linear[i] * response_weight) +
                                  linear_a[i])
                linear_a[i] = f32(linear_a[i] + tangent_motion.linear[i])
                angular_a[i] = f32(f32(normal_motion.angular[i] * response_weight) +
                                   angular_a[i])
                angular_a[i] = f32(angular_a[i] + tangent_motion.angular[i])
        if target_movable:
            normal_motion = impulse_motion(target.inertia, _scale(normal_at_time, -1),
                                           lever_b, radial_b)
            tangent_motion = impulse_motion(target.inertia, _scale(tangential_at_time, -1),
                                            lever_b, radial_b)
            current_linear_b = _add(_add(current_linear_b, tangent_motion.linear),
                                    normal_motion.linear)
            current_angular_b = _add(_add(current_angular_b, tangent_motion.angular),
                                     normal_motion.angular)
            for i in range(3):
                linear_b[i] = f32(f32(normal_motion.linear[i] * response_weight) +
                                  linear_b[i])
                linear_b[i] = f32(linear_b[i] + tangent_motion.linear[i])
                angular_b[i] = f32(f32(normal_motion.angular[i] * response_weight) +
                                   angular_b[i])
                angular_b[i] = f32(angular_b[i] + tangent_motion.angular[i])
        samples += 1

    if samples:
        owner = replace(owner,
            linear_velocity=_add(owner.linear_velocity, linear_a),
            angular_turn_velocity=_add(owner.angular_turn_velocity,
                tuple(f32(value * .15915494) for value in angular_a)),
            contact_record=record_a)
        target = replace(target,
            linear_velocity=_add(target.linear_velocity, linear_b),
            angular_turn_velocity=_add(target.angular_turn_velocity,
                tuple(f32(value * .15915494) for value in angular_b)),
            contact_record=record_b)
    return CollisionImpactResult(samples != 0, owner, target, samples, status, effective_mass)
