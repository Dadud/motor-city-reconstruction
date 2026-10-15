"""Original ordered nearby-vehicle scan and wake geometry, 0x536960."""
from dataclasses import dataclass, replace
import math
from client.tire_response import f32


@dataclass(frozen=True)
class DraftVehicle:
    identifier: int
    position: tuple
    basis: tuple
    half_extents: tuple
    wake_origin: tuple = (0., 0., 0.)
    wake_normals: tuple = ((0., 0., 0.),)*4


@dataclass(frozen=True)
class DraftingOutput:
    factor: float
    vehicles: tuple
    selected_vehicle: int | None
    inside_wake: bool


def _normalize(vehicle):
    if type(vehicle.identifier) is not int or vehicle.identifier < 0:
        raise ValueError('nonnegative stable vehicle identifier required')
    if tuple(map(len, (vehicle.position, vehicle.basis, vehicle.half_extents, vehicle.wake_origin))) != (3, 9, 3, 3):
        raise ValueError('position, basis, extents and wake origin required')
    if len(vehicle.wake_normals) != 4 or any(len(n) != 3 for n in vehicle.wake_normals):
        raise ValueError('four wake plane normals required')
    extent = tuple(map(f32, vehicle.half_extents))
    if min(extent) <= 0:
        raise ValueError('positive vehicle half extents required')
    return replace(vehicle, position=tuple(map(f32, vehicle.position)), basis=tuple(map(f32, vehicle.basis)),
        half_extents=extent, wake_origin=tuple(map(f32, vehicle.wake_origin)),
        wake_normals=tuple(tuple(map(f32, n)) for n in vehicle.wake_normals))


def _dot(a, b):
    return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2]


def _cross(a, b):
    return (f32(a[1]*b[2]-a[2]*b[1]), f32(a[2]*b[0]-a[0]*b[2]), f32(a[0]*b[1]-a[1]*b[0]))


def calculate_drafting(identifier, vehicles):
    cars = list(map(_normalize, vehicles))
    identities = [c.identifier for c in cars]
    if len(set(identities)) != len(identities) or identifier not in identities:
        raise ValueError('unique vehicle IDs including current vehicle required')
    own = cars[identities.index(identifier)]
    length = own.half_extents[2]
    reach = f32(length*6)
    forward = own.basis[6:9]
    sample = tuple(f32(forward[i]*length+own.position[i]) for i in range(3))
    for index, car in enumerate(cars):
        if car.identifier == identifier:
            continue
        dx = f32(own.position[0]-car.position[0])
        dz = f32(own.position[2]-car.position[2])
        distance = f32(math.sqrt(dx*dx+dz*dz))
        if distance > reach:
            continue
        alignment = _dot(forward, car.basis[6:9])
        if alignment < f32(.9659258):
            continue
        stored_alignment = f32(alignment)
        side = [car.basis[i]*car.half_extents[0] for i in range(3)]
        side[0], side[1] = f32(side[0]), f32(side[1])
        up = [car.basis[3+i]*car.half_extents[1] for i in range(3)]
        up[1], up[2] = f32(up[1]), f32(up[2])
        back = [car.basis[6+i]*f32(car.half_extents[2]*4) for i in range(3)]
        back[1], back[2] = f32(back[1]), f32(back[2])
        corners = tuple(tuple(f32(sign_x*side[i]+sign_y*up[i]-back[i]) for i in range(3))
                        for sign_x, sign_y in ((1, 1), (1, -1), (-1, -1), (-1, 1)))
        normals = tuple(_cross(corners[i], corners[(i+1)%4]) for i in range(4))
        origin = tuple(f32(car.half_extents[2]*3*car.basis[6+i]+car.position[i]) for i in range(3))
        cars[index] = replace(car, wake_origin=origin, wake_normals=normals)
        relative = tuple(f32(sample[i]-origin[i]) for i in range(3))
        inside = all(_dot(relative, n) >= 0 for n in normals)
        if inside:
            factor = f32(((f32(1.0340742)-stored_alignment)*(distance+reach)*.25)/(reach*f32(.034074187)))
        else:
            # Original x87 division produces +infinity at coincident horizontal
            # positions; the subsequent clamp then returns 1.25.
            factor = 1.25 if distance == 0 else max(1., min(1.25, f32((length/distance)*.25+1)))
        return DraftingOutput(factor, tuple(cars), car.identifier, inside)
    return DraftingOutput(1., tuple(cars), None, False)
