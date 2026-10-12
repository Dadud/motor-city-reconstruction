"""Recovered active-motion increments; force solver and schedule pending.

REA 160/164: 0x540c30 integrates world linear acceleration with 1/32.
REA 157: 0x53c140 uses the same interval for angular acceleration.
REA 178–188: 0x520450 advances pose by 1/64; 169 predicts supports by 1/48.
This implements those arithmetic updates, not native inactive-motion gating,
collision response or x87 extended-precision equivalence.
"""
import math
from .contact import Pose


SIMULATION_STEP = 1 / 32
POSE_STEP = 1 / 64
SUPPORT_LOOKAHEAD = 1 / 48


def _vectors(*vectors):
    if any(len(v) != 3 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('finite three-component motion vectors are required')


def _multiply(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3))
                       for j in range(3)) for i in range(3))


def advance_pose(pose, linear, angular, center_of_mass=(0, 0, 0)):
    """Recovered active pose arithmetic for one 1/64-second update.

    World angular velocity is radians/second. Native row-vector matrices compose
    X/Y/Z increments; transposing to Pose's column-vector convention gives
    Rz @ Ry @ Rx @ rotation. Translate the world COM, then recover body origin.
    Native execution gates, periodic matrix repair and collision logic are outside
    this helper. This does not establish how frequently the scheduler calls it.
    """
    _vectors(linear, angular, center_of_mass)
    x, y, z = (a * POSE_STEP for a in angular)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))
    rotation = _multiply(_multiply(_multiply(rz, ry), rx), pose.rotation)
    old_com = pose.transform(center_of_mass)
    position = tuple(old_com[i] + linear[i] * POSE_STEP -
                     sum(rotation[i][j] * center_of_mass[j] for j in range(3))
                     for i in range(3))
    return Pose(position, rotation)


def support_pose(pose, linear):
    """0x53d320 terrain look-ahead: translate by v/48, preserve rotation.

    This predicts the query location only; it does not advance simulation state.
    """
    _vectors(linear)
    return Pose(tuple(pose.position[i] + linear[i] * SUPPORT_LOOKAHEAD
                      for i in range(3)), pose.rotation)


def advance_velocity(velocity, acceleration):
    """Advance a finite world vector by one native simulation interval.

    Linear units are meters/second and meters/second squared. Angular callers
    use radians/second and radians/second squared consistently; native angular
    storage uses turns, but the constant increment commutes with conversion.
    No position or orientation update is implied.
    """
    _vectors(velocity, acceleration)
    result = tuple(v + a * SIMULATION_STEP for v, a in zip(velocity, acceleration))
    if not all(math.isfinite(x) for x in result):
        raise ValueError('velocity increment overflowed')
    return result
