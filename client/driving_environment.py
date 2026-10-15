"""Recovered body/environment stages on the force controller's shared state."""
from dataclasses import dataclass, replace
from client.body_environment import BodyEnvironment, calculate_body_environment
from client.body_resistance import BodyResistanceState
from client.body_vertical_load import BodyVerticalLoadState, adjust_body_vertical_load


@dataclass
class EnvironmentInputs:
    body: BodyResistanceState
    vertical: BodyVerticalLoadState
    environment: BodyEnvironment


class DrivingEnvironment:
    """Wrap a DrivingForces external executor, preserving cross-car wake writes.

    Geometry, pitch, weather, counters and nearby-car records absent from the
    controller remain explicit inputs. In particular, wind's original +0x9c
    transform is not silently equated to the prepared +0xc34 controller matrix.
    The remaining executor updates these inputs when their producers run.
    """
    stages = frozenset(('body_moment_inputs', 'body_forces'))

    def __init__(self, inputs, external):
        if not isinstance(inputs, EnvironmentInputs) or not callable(external):
            raise ValueError('explicit environment inputs and remaining stages required')
        self.inputs, self.external = inputs, external
        self.last_environment = None

    @staticmethod
    def _loads(s, loads):
        for w, load in zip(s.wheels, loads):
            w.force = (w.force[0], load, w.force[2])

    def __call__(self, call, s, force):
        if call.stage not in self.stages:
            return self.external(call, s, force)
        p = self.inputs
        if call.stage == 'body_moment_inputs':
            # Configuration +0x2c/+0x38 have one value in the original owner.
            # ForceInputs already owns their canonical typed views.
            p.body = replace(p.body, speed=s.speed, longitudinal_speed=s.local_linear[2],
                secondary_angle=s.secondary_angle, front_lever=s.front_lever,
                rear_lever=s.rear_lever, length_parameter=force.tire.wheelbase,
                height_parameter=force.moments.height_parameter,
                resistance_disabled=bool(s.flags & 0x200),
                wheel_loads=tuple(w.force[1] for w in s.wheels),
                contacts=tuple(w.contact for w in s.wheels))
            out = calculate_body_environment(p.body, p.environment)
            self.last_environment = out
            # A selected peer's wake geometry is an original write, not a cache
            # discarded after calculating this car's drafting multiplier.
            p.environment = replace(p.environment, vehicles=out.drafting.vehicles)
            s.longitudinal_contribution = out.body.longitudinal_drag
            s.lateral_contribution = out.body.yaw_contribution
            s.body_moment = out.body.pitch_contribution
            self._loads(s, out.body.wheel_loads)
        else:
            p.vertical = replace(p.vertical, speed=s.speed,
                longitudinal_speed=s.local_linear[2], front_quality=force.spin.front_quality,
                rear_quality=force.spin.rear_quality,
                wheel_loads=tuple(w.force[1] for w in s.wheels))
            out = adjust_body_vertical_load(p.vertical)
            s.front_moment, s.rear_moment, s.gravity_force = (
                out.front_vertical, out.rear_vertical, out.total_vertical)
            self._loads(s, out.wheel_loads)
