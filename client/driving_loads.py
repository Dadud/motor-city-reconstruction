"""Recovered load producers composed with the shared driving force controller.

Configuration/context values absent from VehicleUpdateState remain explicit.
No stock defaults, suspension model or component effects are invented here.
"""
from dataclasses import dataclass, replace
from client.normal_load import NormalLoadInput, normal_load
from client.load_transfer import LoadTransferInput, transfer_load
from client.suspension_load_correction import SuspensionLoadInput, correct_suspension_load
from client.wheel_speed import WheelSpeedInput, WheelSpeedState, project_wheel_speeds
from client.rolling_resistance import ResistanceWheel, rolling_resistance


# These three original load routines use a different rear-wheel accumulator order
# from the consecutive owner-record order used by tires/spin/controller forces.
LOAD_ORDER = (0, 1, 3, 2)


@dataclass
class LoadParameters:
    configuration_mass: float
    wheelbase: float
    front_track: float
    rear_track: float
    height_parameter: float
    pitch: float
    bank: float
    suspension_pitch: float
    mass_offset: float
    front_weight_parameter: float
    rear_weight_parameter: float
    gear_factor: float
    torque: float
    component_mode: int
    front_resistance: float
    rear_resistance: float


class DrivingLoads:
    """Use as DrivingForces.external; other children remain mandatory behavior.

    external(call, controller, force_inputs) executes every unbound stage and
    query. resistance_mode(controller, force_inputs, parameters) supplies the
    original mode predicate only when its actual gate is reached. Producers may
    update the retained parameters before a later load stage consumes them.

    The wheel support-correction record held by force_inputs.moments also owns
    normal-load scales (+0x74). force_inputs.spin owns the front/rear scale and
    secondary body-angle aliases. Configuration geometry here owns the matching
    tire/moment values. Controller mass remains a distinct owner field.
    """
    stages = frozenset(('normal_loads', 'project_wheels', 'load_transfer',
                        'suspension_loads', 'resistance'))

    def __init__(self, parameters, external, resistance_mode):
        if not isinstance(parameters, LoadParameters):
            raise ValueError('explicit recovered load parameters required')
        if not callable(external) or not callable(resistance_mode):
            raise ValueError('remaining child executor and resistance mode observation required')
        self.parameters = parameters
        self.external = external
        self.resistance_mode = resistance_mode

    @staticmethod
    def _write_loads(s, loads):
        for index, load in zip(LOAD_ORDER, loads):
            w = s.wheels[index]
            w.force = (w.force[0], load, w.force[2])

    def __call__(self, call, s, force_inputs):
        if call.stage not in self.stages:
            return self.external(call, s, force_inputs)
        p, f = self.parameters, force_inputs
        if any(len(record.wheels) != 4 for record in (f.tire, f.spin, f.moments)) or len(s.wheels) != 4:
            raise ValueError('four shared wheel records required')
        # These are the same configuration fields consumed by the later stages,
        # not independently retained copies that can silently diverge.
        f.tire = replace(f.tire, front_track=p.front_track, wheelbase=p.wheelbase)
        f.moments = replace(f.moments, mass_parameter=p.configuration_mass,
            front_track=p.front_track, rear_track=p.rear_track, height_parameter=p.height_parameter)
        wheels = tuple(s.wheels[index] for index in LOAD_ORDER)
        if call.stage == 'normal_loads':
            loads = normal_load(NormalLoadInput(tuple(w.contact for w in wheels), p.pitch, p.bank,
                p.configuration_mass, p.wheelbase, p.front_track, p.rear_track, p.height_parameter,
                s.front_lever, s.rear_lever, s.speed, s.turning_radius_y, s.local_acceleration[1],
                tuple(f.moments.wheels[index].support_correction for index in LOAD_ORDER)))
            for index, load in zip(LOAD_ORDER, loads):
                s.wheels[index].force = (0., load, 0.)
        elif call.stage == 'project_wheels':
            speeds = project_wheel_speeds(WheelSpeedState(tuple(WheelSpeedInput(w.primary_angle,
                w.contact, w.spin, w.spin_scale) for w in s.wheels), s.local_linear[0],
                s.local_linear[2], s.local_angular[1], s.front_lever, s.rear_lever,
                p.front_track, p.rear_track))
            for w, speed in zip(s.wheels, speeds):
                w.projected_speed = speed
        elif call.stage == 'load_transfer':
            loads = transfer_load(LoadTransferInput(tuple(w.force[1] for w in wheels), p.pitch,
                s.local_acceleration[2], s.local_acceleration[0], s.speed, p.configuration_mass,
                p.wheelbase, p.front_track, p.rear_track, p.height_parameter,
                f.spin.front_scale, f.spin.rear_scale))
            self._write_loads(s, loads)
        elif call.stage == 'suspension_loads':
            loads = correct_suspension_load(SuspensionLoadInput(tuple(w.force[1] for w in wheels),
                tuple(w.contact for w in wheels), p.pitch, s.support_count != 0, s.speed,
                f.spin.body_secondary_angle, p.suspension_pitch, p.configuration_mass, p.mass_offset,
                p.front_weight_parameter, p.rear_weight_parameter, s.front_lever, s.rear_lever,
                p.wheelbase, p.rear_track, p.gear_factor, p.torque, p.component_mode, bool(s.flags & 2)))
            self._write_loads(s, loads)
        elif call.stage == 'resistance':
            mode = False
            disabled = bool(s.flags & 0x200)
            if abs(s.speed) >= 2 and not disabled:
                mode = self.resistance_mode(s, f, p)
                if type(mode) is not bool:
                    raise ValueError('boolean original resistance mode observation required')
            result = rolling_resistance(tuple(ResistanceWheel(tire.slip_angle, w.tire_type,
                w.force[1], w.spin, w.spin_scale, w.contact, w.force[2])
                for w, tire in zip(s.wheels, f.tire.wheels)), s.speed,
                p.front_resistance, p.rear_resistance, s.front_grip_gate, s.rear_grip_gate,
                p.pitch, disabled_flag=disabled, mode_predicate=mode, alternate=s.orientation_disabled)
            for w, out in zip(s.wheels, result.wheels):
                w.force = (w.force[0], w.force[1], out.longitudinal_force)
