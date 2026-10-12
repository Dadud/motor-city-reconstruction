"""Authored fixed-step driving model, independent of the unfinished native dyno.

This bicycle model provides a controllable offline drive on decoded terrain.
Its acceleration, drag and grip are design parameters, not recovered MCO forces.
Missing wheel supports stop movement; object collisions remain unimplemented.
"""
from dataclasses import dataclass
import math

from .contact import Pose

STEP = 1 / 120


@dataclass(frozen=True)
class Controls:
    throttle: float = 0
    brake: float = 0
    steering: float = 0
    reverse: bool = False

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.throttle, self.brake, self.steering)):
            raise ValueError('non-finite driving input')
        if not (0 <= self.throttle <= 1 and 0 <= self.brake <= 1 and -1 <= self.steering <= 1):
            raise ValueError('driving input outside control range')


def _unit(vector):
    size = math.sqrt(sum(v*v for v in vector))
    if size < 1e-9:
        raise ValueError('degenerate terrain basis')
    return tuple(v/size for v in vector)


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


class Drive:
    def __init__(self, world, trial=None):
        self.world = world
        self.trial = trial
        front = sum(p[2] for p in world.rig.centers[:2])/2
        rear = sum(p[2] for p in world.rig.centers[2:])/2
        self.wheelbase = abs(front-rear)
        if not .5 <= self.wheelbase <= 10:
            raise ValueError('unsupported wheelbase for driving')
        self.reset()

    def reset(self):
        if self.trial:
            self.trial.reset()
        self.pose = self.world.pose
        self.heading = math.atan2(self.pose.rotation[0][2], self.pose.rotation[2][2])
        self.speed = self.steering = self.elapsed = self.distance = self.accumulator = 0
        self.blocked = False
        self.contacts = self.world.contacts

    def update(self, dt, controls=Controls()):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('invalid frame interval')
        # Bound catch-up after focus loss; simulation time excludes discarded time.
        self.accumulator += min(dt, .25)
        ticks = 0
        while self.accumulator+1e-12 >= STEP:
            self._step(controls)
            self.accumulator = max(0, self.accumulator-STEP)
            ticks += 1
        return ticks

    def _supported_pose(self, x, z, heading):
        position = (x, self.pose.position[1], z)
        flat = Pose.yaw(position, heading)
        contacts = self.world.rig.contacts(self.world.terrain, flat, self.world.radii)
        if any(c.height is None for c in contacts):
            return None
        up = _unit(tuple(sum(c.normal[i] for c in contacts) for i in range(3)))
        forward = (math.sin(heading), 0, math.cos(heading))
        right = _unit(_cross(up, forward))
        forward = _unit(_cross(right, up))
        rotation = tuple((right[i], up[i], forward[i]) for i in range(3))
        candidate = Pose(position, rotation)
        # Re-query tilted wheel locations before accepting the new support plane.
        try:
            return self.world.rig.spawn_pose(self.world.terrain, candidate, self.world.radii)
        except ValueError:
            return None

    def _step(self, controls):
        # Sprint finish enters a stationary result screen until the player resets.
        if self.trial and self.trial.finished:
            return
        self.elapsed += STEP
        target = controls.steering*math.radians(30)
        change = min(abs(target-self.steering), math.radians(100)*STEP)
        self.steering += math.copysign(change, target-self.steering)
        direction = -1 if controls.reverse else 1
        # Switching direction first brakes the car to a halt.
        opposite = self.speed*direction < -.1
        braking = max(controls.brake, controls.throttle if opposite else 0)
        acceleration = 0 if opposite else direction*controls.throttle*5.0
        drag = .18 + .002*self.speed*self.speed
        next_speed = self.speed+acceleration*STEP
        resistance = (drag+braking*10)*STEP
        next_speed = math.copysign(max(0, abs(next_speed)-resistance), next_speed)
        next_speed = max(-12, min(55, next_speed))
        yaw_rate = next_speed*math.tan(self.steering)/self.wheelbase
        # Limit lateral acceleration to a conservative authored grip bound.
        maximum_yaw = 7/max(abs(next_speed), 1)
        yaw_rate = max(-maximum_yaw, min(maximum_yaw, yaw_rate))
        heading = math.remainder(self.heading+yaw_rate*STEP, math.tau)
        forward = self.pose.rotation
        x = self.pose.position[0]+forward[0][2]*next_speed*STEP
        z = self.pose.position[2]+forward[2][2]*next_speed*STEP
        supported = self._supported_pose(x, z, heading)
        self.blocked = supported is None
        if self.blocked:
            self.speed = 0
            if self.trial:
                self.trial.update(self.pose.position, self.pose.position, STEP)
            return
        pose, contacts = supported
        if self.trial:
            self.trial.update(self.pose.position, pose.position, STEP)
        self.distance += math.hypot(x-self.pose.position[0], z-self.pose.position[2])
        self.pose, self.contacts = pose, contacts
        self.heading, self.speed = heading, next_speed
        if self.trial and self.trial.finished:
            self.speed = 0
