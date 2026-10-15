"""Recovered force stages connected to the original typed vehicle controller.

Controller fields are authoritative at every call, including writes made by
external stages. Templates supply only fields absent from that controller view.
Unknown stages and component effects require explicit consumers.
"""
from dataclasses import dataclass, replace
from client.tire_update import update_tires, TireWheel, TireUpdateState
from client.wheel_force_correction import ForceCorrectionWheel, correct_wheel_forces
from client.wheel_spin import integrate_wheel_spin, WheelSpinState
from client.combined_slip import CombinedSlipWheel, CombinedSlipState, limit_combined_slip
from client.wheel_force_orientation import ForceOrientationWheel, orient_wheel_forces
from client.body_moments import MomentWheel, accumulate_body_moments, BodyMomentState


@dataclass
class ForceInputs:
    tire: TireUpdateState
    spin: WheelSpinState
    moments: BodyMomentState
    service_control: float
    other_control: float
    parking_control: bool
    orientation_front: float
    orientation_rear: float


class DrivingForces:
    """Stateful child executor; retain this instance across successive ticks.

    external(call, controller, inputs) must execute every unbound child/query.
    effects(kind, events, controller, inputs) receives ordered events immediately
    after their originating stage, before the next child consumes shared state.
    Neither callback has a default implementation.
    """
    stages = frozenset(('tires', 'wheel_correction', 'wheel_spin',
                        'combined_slip', 'force_orientation', 'body_moments'))

    def __init__(self, inputs, external, effects):
        if not callable(external) or not callable(effects):
            raise ValueError('external stages and component effect consumers required')
        if any(len(record.wheels) != 4 for record in (inputs.tire, inputs.spin, inputs.moments)):
            raise ValueError('four wheel records required in every input view')
        self.inputs, self.external, self.effects = inputs, external, effects

    def __call__(self, call, s):
        p = self.inputs
        if call.stage not in self.stages:
            return self.external(call, s, p)
        if call.stage == 'tires':
            wheels = tuple(TireWheel(w.primary_angle, old.slip_angle, spin.secondary_angle,
                w.projected_speed, w.force[1], w.contact, w.quality,
                w.force[0], w.force[2], old.secondary_response)
                for w, old, spin in zip(s.wheels, p.tire.wheels, p.spin.wheels))
            p.tire = update_tires(replace(p.tire, wheels=wheels, speed=s.speed,
                mass_parameter=s.mass, front_lever=s.front_lever, rear_lever=s.rear_lever,
                maximum_steering=s.maximum_steering, longitudinal_velocity=s.local_linear[2],
                lateral_velocity=s.local_linear[0], lateral_acceleration=s.local_acceleration[0],
                yaw_rate=s.local_angular[1], body_slip=s.secondary_angle,
                alternate_load=s.orientation_disabled))
            s.local_linear = (p.tire.lateral_velocity, s.local_linear[1], s.local_linear[2])
            s.local_acceleration = (p.tire.lateral_acceleration, *s.local_acceleration[1:])
            s.local_angular = (s.local_angular[0], p.tire.yaw_rate, s.local_angular[2])
            for w, out in zip(s.wheels, p.tire.wheels):
                w.primary_angle = out.steering_angle
                w.force = (out.lateral_force, w.force[1], out.longitudinal_force)
        elif call.stage == 'wheel_correction':
            corrected = correct_wheel_forces(tuple(ForceCorrectionWheel(w.projected_speed,
                w.spin, old.spin_adjustment, w.spin_scale, w.force[0], w.force[2], w.force[1],
                w.primary_coefficient, w.secondary_coefficient, w.contact, old.correction_enabled)
                for w, old in zip(s.wheels, p.spin.wheels)), p.service_control, p.other_control,
                p.parking_control, p.spin.direction_mode, p.spin.override_control)
            for w, out in zip(s.wheels, corrected):
                w.spin = out.spin_value
            p.spin = replace(p.spin, wheels=tuple(replace(old, spin_adjustment=out.spin_adjustment)
                for old, out in zip(p.spin.wheels, corrected)))
        elif call.stage == 'wheel_spin':
            result = integrate_wheel_spin(replace(p.spin, wheels=tuple(replace(old,
                spin_value=w.spin, spin_scale=w.spin_scale, projected_speed=w.projected_speed,
                normal_load=w.force[1], phase=w.phase, contact=w.contact)
                for w, old in zip(s.wheels, p.spin.wheels)), front_lever=s.front_lever,
                rear_lever=s.rear_lever, yaw_rate=s.local_angular[1], lateral_velocity=s.local_linear[0]))
            p.spin = result.state
            for w, out in zip(s.wheels, p.spin.wheels):
                w.spin, w.spin_scale, w.phase = out.spin_value, out.spin_scale, out.phase
                w.local_lateral = out.local_lateral
            self.effects('wheel_spin', result.wear_events, s, p)
        elif call.stage == 'combined_slip':
            result, events = limit_combined_slip(CombinedSlipState(tuple(CombinedSlipWheel(
                spin.slip_ratio, w.force[0], w.force[2], tire.secondary_response, w.force[1],
                w.primary_coefficient, w.secondary_coefficient, w.spin, w.spin_scale,
                w.projected_speed, w.contact, w.surface_class, w.wear_mode)
                for w, tire, spin in zip(s.wheels, p.tire.wheels, p.spin.wheels)), s.speed,
                p.parking_control, s.orientation_disabled, s.front_grip_gate, s.rear_grip_gate,
                s.environment_mode))
            for w, out in zip(s.wheels, result.wheels):
                w.force = (out.lateral_force, w.force[1], out.longitudinal_force)
            p.tire = replace(p.tire, wheels=tuple(replace(old, secondary_response=out.secondary_response)
                for old, out in zip(p.tire.wheels, result.wheels)))
            self.effects('combined_slip', events, s, p)
        elif call.stage == 'force_orientation':
            result = orient_wheel_forces(tuple(ForceOrientationWheel(w.primary_angle, w.phase,
                w.force[0], w.force[2]) for w in s.wheels), p.orientation_front, p.orientation_rear)
            for w, out in zip(s.wheels, result):
                w.force = (out.lateral_force, w.force[1], out.longitudinal_force)
        elif call.stage == 'body_moments':
            p.moments = replace(p.moments, wheels=tuple(MomentWheel(w.force[0], w.force[2],
                tire.secondary_response, old.support_correction, w.contact)
                for w, tire, old in zip(s.wheels, p.tire.wheels, p.moments.wheels)), speed=s.speed,
                front_lever=s.front_lever, rear_lever=s.rear_lever, inverse_pitch=s.angular_scale,
                front_vertical=s.front_moment, rear_vertical=s.rear_moment,
                yaw_contribution=s.lateral_contribution, alternate_mode=s.orientation_disabled)
            s.local_angular_acceleration = accumulate_body_moments(p.moments)
