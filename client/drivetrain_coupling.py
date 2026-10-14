"""Verified torque-output tail 0x547932–0x5479fe, before the RPM call.

Neutral is observed gear slot 1. Gear-index producers and engagement producers
remain external. Environment correction executes the complete 0x535e20 helper.
"""
from dataclasses import dataclass
from client.tire_response import f32


@dataclass(frozen=True)
class DrivetrainCoupling:
    rpm: int
    curve_torque: float
    effective_torque: float
    drag_factor: float
    drag_speed: float
    gear_index: int
    engagement: float
    coupling_resistance: float
    environment_field: float
    environment_override: bool
    environment_selector_enabled: bool
    environment_selector: int


@dataclass(frozen=True)
class DrivetrainCouplingOutput:
    power: float
    drag: float
    corrected_torque: float
    acceleration_input: float
    environment_correction: float


def environment_correction(field, override, selector_enabled, selector):
    if type(override) is not bool or type(selector_enabled) is not bool or type(selector) is not int:
        raise ValueError('environment mode fields require booleans and an integer')
    field = f32(field)
    base = f32(278.15) if override else f32(288.15)
    selected = selector if selector_enabled else 0
    if selected == 2: base -= 20
    elif selected == 1: base -= 10
    correction = f32(f32(1.25)-(base*f32(.00087)+f32(field+500)*f32(.000002173)))
    return min(max(correction, f32(.95)), f32(1.05))


def couple_drivetrain(state):
    if type(state.rpm) is not int or type(state.gear_index) is not int:
        raise ValueError('RPM and gear index must be integers')
    curve, torque, drag_factor, drag_speed, engagement, resistance = map(f32, (
        state.curve_torque, state.effective_torque, state.drag_factor,
        state.drag_speed, state.engagement, state.coupling_resistance))
    correction = environment_correction(state.environment_field, state.environment_override,
            state.environment_selector_enabled, state.environment_selector)
    power = max(f32(state.rpm*curve*f32(.00010471976)), 0.0)
    drag = f32(drag_factor*drag_speed)
    # The original stores the corrected torque, while its x87 value continues
    # into the engagement branches before the final float store.
    corrected = correction*torque-drag
    if state.gear_index == 1 or engagement == 0:
        acceleration = corrected
    elif engagement >= 1:
        acceleration = -resistance + min(corrected, 0.0)
    else:
        acceleration = (1-engagement*engagement)*corrected-resistance
    return DrivetrainCouplingOutput(power, drag, f32(corrected), f32(acceleration), correction)
