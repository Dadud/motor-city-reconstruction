"""Standalone recovered nineteen-knot core dyno, for unboosted records only.

This reproduces the numerical core, not the game's final curve corrections or
vehicle-driving forces. Native field conventions are retained.
"""
from dataclasses import replace
import math
import struct
from .dyno import intake_rpm_correction
from .dyno_solver import (_f32, cylinder_geometry, valve_events, cam_profiles,
    flow_coefficients, valve_lift, airflow_area, work_outputs)
from .thermodynamics import (initial_cylinder_state, intake_boundary,
    charge_temperature, exhaust_parameters, cycle_preparation, exhaust_phase_factor,
    exhaust_wave_value, intake_pressure_feedback, IntakeExchange,
    intake_mass_exchange, exhaust_mass_transfer)
from .cylinder_integration import (IntegrationInputs, IntegrationState,
    integrate_crank_step, crank_step_size, carry_cycle_pressure)


def solve_core_record(record):
    """Return a mutated 1004-byte core record with all seven nineteen-knot series.

    Boost modes are explicitly unsupported; their helper is not substituted by
    a guessed model. Valid assembled inputs must satisfy the recovered stages.
    """
    if not isinstance(record, bytes) or len(record) != 1004:
        raise ValueError('expected a 1004-byte assembled dyno record')
    def floating(offset):
        return struct.unpack_from('<f',record,offset)[0]
    def short(offset):
        return struct.unpack_from('<h',record,offset)[0]
    if short(0x3c4) != 0:
        raise ValueError('boosted dyno records are not recovered by this driver')
    bore,stroke,compression = (floating(o) for o in (0x8c,0x90,0xa0))
    geometry = cylinder_geometry(bore,stroke,compression,short(0x94))
    events = valve_events(record)
    if not all(math.isfinite(v) and abs(v) <= 1440 for v in
               (events.angle_a8,events.angle_ac,events.angle_b0,events.angle_b4)):
        raise ValueError('valve angles outside supported core domain')
    if not math.isfinite(floating(0x308)):
        raise ValueError('non-finite additional power input')
    exhaust_cam,intake_cam = cam_profiles(record)
    flow = flow_coefficients(record)
    intake_points = struct.unpack_from('<10f',record,0x34c)
    exhaust_points = struct.unpack_from('<10f',record,0x39c)
    train = short(0x84)
    fuel_ratio = {2:12.0,3:11.5}.get(train,12.5)
    mode = short(0x2dc)
    fuel_energy = (19800 if 10 <= mode <=18 else {19:19100,20:18600,21:18839}.get(mode,19000))
    output = bytearray(record)
    pressure,end_pressure = 0.0,0.0
    previous = IntakeExchange()
    intake_pressure = 0.0
    exhaust_wave = 0.0
    consumed_mass = 0.0
    preceding_fill = 70.0
    phase = exhaust_phase_factor(events.angle_a8)
    scale = _f32(events.intake_size*_f32(.85))
    extra = _f32(floating(0x308)*25)
    for knot,rpm in enumerate(range(2000,11001,500)):
        step = crank_step_size(rpm)
        charge = charge_temperature(mode,rpm)
        correction = intake_rpm_correction(short(0x6e),rpm,floating(0x70))
        pressure = carry_cycle_pressure(knot,pressure,end_pressure)
        initial = initial_cylinder_state(geometry,stroke,events.angle_a8,pressure)
        state = IntegrationState(initial.pressure,initial.temperature,initial.mass_term)
        boundary = intake_boundary(geometry,rpm,short(0xa4),short(0xa6),short(0x6e))
        boundary_flow = ((geometry.total_displacement*rpm)*preceding_fill)*_f32(.01)/boundary.capacity_scale
        boundary = replace(boundary,pressure=_f32(_f32(14.7)-boundary_flow*boundary_flow*_f32(7.916e-6)))
        exhaust = exhaust_parameters(short(0x7a),rpm,floating(0x7c))
        preparation = cycle_preparation(rpm,charge,exhaust)
        angle = events.angle_a8
        wave = 0.0
        accumulated = 0.0
        iterations = 0
        while angle <= events.angle_a8+720:
            iterations += 1
            if iterations > 2000:
                raise ValueError('cylinder cycle exceeded angle-step bound')
            intake_lift = valve_lift(intake_cam,events.angle_b0,events.angle_b4,angle)
            exhaust_lift = valve_lift(exhaust_cam,events.angle_a8,events.angle_ac,angle)
            intake_area = (airflow_area(intake_lift,intake_points,flow.series_324,
                events.intake_size,pressure_ratio=_f32(intake_pressure/state.pressure))
                if events.angle_b0 < angle < events.angle_b4 else 0.0)
            exhaust_area = (airflow_area(exhaust_lift,exhaust_points,flow.series_374,
                events.exhaust_size) if events.angle_a8 < angle < events.angle_ac else 0.0)
            exhaust_wave = exhaust_wave_value(angle,events.angle_a8,phase,rpm,exhaust,
                                             preparation.exhaust_wave_scale,exhaust_wave)
            if 510 < angle <=540:
                wave = _f32((angle-510)*correction*_f32(.02857142873108387))
            elif 540 < angle <650:
                wave = _f32(math.sin((angle-540)*preparation.angle_step_factor*
                                    _f32(.017453292))*correction)
            intake_pressure = intake_pressure_feedback(boundary.pressure,intake_area,
                                                       scale,previous,wave)
            previous = intake_mass_exchange(state.pressure,state.temperature,intake_pressure,
                charge,intake_area,rpm,replace(previous,pressure_ratio=scale))
            if intake_area > 0:
                accumulated = _f32(previous.mass_delta*step+accumulated)
                consumed_mass = accumulated
            exhaust_delta = exhaust_mass_transfer(state.pressure,state.temperature,
                                                   exhaust_wave,exhaust_area,rpm)
            result = integrate_crank_step(state,IntegrationInputs(angle,step,rpm,
                initial.crank_radius,geometry.rod_length,initial.rod_ratio,initial.piston_area,
                geometry.clearance_volume,bore,geometry.area_term,previous.mass_delta,
                exhaust_delta,intake_pressure,exhaust_wave,preparation.temperature_term,
                consumed_mass,fuel_ratio,fuel_energy))
            if result.angle <= angle:
                raise ValueError('cylinder angle failed to advance')
            state,angle = result.state,result.angle
        pressure = end_pressure = state.pressure
        values = work_outputs(rpm,stroke,state.work,geometry.swept_volume,
                              boundary.displacement_rate,0,extra)
        for offset,value in zip((0xc4,0x110,0x1f4,0x240,0x28c),values):
            struct.pack_into('<f',output,offset+knot*4,value)
        struct.pack_into('<f',output,0x15c+knot*4,boundary.pressure)
        preceding_fill = _f32(consumed_mass/initial.reference_mass_term*100)
        struct.pack_into('<f',output,0x1a8+knot*4,preceding_fill)
    return bytes(output)
