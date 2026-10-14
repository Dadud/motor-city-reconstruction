"""Recovered crank-step integration, in original numeric field conventions."""
from dataclasses import dataclass
import math
from .dyno_solver import _f32
from .thermodynamics import cylinder_energy_terms, _stored_inputs


@dataclass(frozen=True)
class IntegrationState:
    pressure: float
    temperature: float
    mass: float
    previous_pressure_rate: float = 0
    previous_temperature_rate: float = 0
    previous_mass_rate: float = 0
    intake_energy: float = 0
    exhaust_energy: float = 0
    wall_energy: float = 0
    work: float = 0


@dataclass(frozen=True)
class IntegrationInputs:
    angle: float
    step: float
    rpm: float
    crank_radius: float
    rod_length: float
    rod_ratio: float
    piston_area: float
    clearance_volume: float
    bore: float
    wall_area_term: float
    intake_delta: float
    exhaust_delta: float
    intake_pressure: float
    exhaust_pressure: float
    charge_energy: float
    accumulated_intake_mass: float
    fuel_ratio: float
    fuel_energy: float


@dataclass(frozen=True)
class IntegrationResult:
    state: IntegrationState
    angle: float
    volume: float
    pressure_rate: float
    temperature_rate: float
    mass_rate: float
    intake_specific_energy: float
    exhaust_specific_energy: float


def integrate_crank_step(state, inputs):
    """REA 221, 0x47ae8f–0x47b285: evolve pressure, temperature, mass and work.

    The native two-step method retains the preceding derivatives. Valve transfer
    and accumulated intake mass must already reflect the current flow stage.
    No physical unit conversion or missing valve/boost stage is invented here.
    """
    if not isinstance(state, IntegrationState) or not isinstance(inputs, IntegrationInputs):
        raise ValueError('expected recovered integration state and inputs')
    s = IntegrationState(*_stored_inputs(*state.__dict__.values()))
    p = IntegrationInputs(*_stored_inputs(*inputs.__dict__.values()))
    if min(s.pressure, s.temperature, s.mass, p.step, p.rpm, p.crank_radius,
           p.rod_length, p.piston_area, p.clearance_volume, p.bore) <= 0 or p.fuel_ratio <= -1:
        raise ValueError('invalid integration domain')
    radians = _f32(.017453292)
    sine, cosine = _f32(math.sin(p.angle*radians)), _f32(math.cos(p.angle*radians))
    projection = _f32(p.crank_radius/p.rod_length*sine)
    root = math.sqrt(1-projection*projection)
    volume = _f32(((1-root)*p.rod_ratio+(1-cosine))*p.piston_area*p.crank_radius+p.clearance_volume)
    volume_rate = ((p.crank_radius*cosine/p.rod_length)/root+1)*p.piston_area*p.crank_radius*sine*radians
    terms = cylinder_energy_terms(s.temperature)
    enthalpy = s.temperature*_f32(.06857)+terms.energy_term
    intake_energy = _f32(enthalpy) if s.pressure > p.intake_pressure else p.charge_energy
    exhaust_energy = _f32(506.7442626953125) if p.exhaust_pressure > s.pressure else _f32(enthalpy)
    intake_total = _f32(p.intake_delta*p.step*intake_energy+s.intake_energy)
    exhaust_total = _f32(p.step*exhaust_energy*p.exhaust_delta+s.exhaust_energy)
    wall = (_f32(1.7e-5)/(p.rpm*6))*(volume*4/p.bore+p.wall_area_term)*(800-s.temperature)*17
    wall_total = _f32(p.step*wall+s.wall_energy)
    combustion = (math.sin((p.angle-710)*_f32(.05235988))*_f32(.02617994)
                  if 710 < p.angle < 770 else 0)
    net = _f32(p.intake_delta-p.exhaust_delta)
    pressure_volume_rate = _f32(volume_rate*s.pressure)
    capacity = terms.capacity_term*_f32(14.587892532348633)
    energy_rate = p.accumulated_intake_mass/(p.fuel_ratio+1)*p.fuel_energy*combustion+wall
    conversion = _f32(.00010711225331760943)
    energy_rate -= pressure_volume_rate*conversion
    energy_rate += p.intake_delta*intake_energy
    energy_rate -= exhaust_energy*p.exhaust_delta
    energy_rate -= pressure_volume_rate*capacity*conversion
    energy_rate += (s.temperature*terms.capacity_term-terms.energy_term)*net
    pressure_rate = energy_rate/(capacity*volume)*9336
    temperature_rate = _f32(((volume*pressure_rate+pressure_volume_rate)*conversion-
                             s.temperature*net*_f32(.06857))/(s.mass*_f32(.06857)))
    pressure = _f32((pressure_rate*1.5-s.previous_pressure_rate*.5)*p.step+s.pressure)
    temperature = _f32((temperature_rate*1.5-s.previous_temperature_rate*.5)*p.step+s.temperature)
    mass = _f32((net*1.5-s.previous_mass_rate*.5)*p.step+s.mass)
    angle = _f32(p.angle+p.step)
    next_radians = _f32((p.angle+p.step)*radians)
    raw_projection = p.crank_radius/p.rod_length*math.sin(next_radians)
    next_projection = _f32(raw_projection)
    next_volume = ((1-math.sqrt(1-raw_projection*next_projection))*p.rod_ratio+
                   (1-math.cos(next_radians)))*p.piston_area*p.crank_radius+p.clearance_volume
    work = _f32((next_volume-volume)*(pressure+s.pressure)*.5+s.work)
    result = IntegrationState(pressure, temperature, mass, _f32(pressure_rate),
        temperature_rate, net, intake_total, exhaust_total, wall_total, work)
    return IntegrationResult(result, angle, volume, _f32(pressure_rate), temperature_rate,
                             net, intake_energy, exhaust_energy)




def crank_step_size(rpm):
    """0x479bb6–0x479bcb: native RPM-dependent angle interval."""
    if type(rpm) is not int or rpm not in range(2000, 11001, 500):
        raise ValueError('RPM must be a supported dyno knot')
    return _f32(rpm*_f32(.0003))


def carry_cycle_pressure(knot_index, preceding_pressure, stored_end_pressure):
    """0x479e2a–0x479e4d pressure selection between nineteen RPM knots.

    Knot zero starts at 44.1; knot one retains live pressure; later knots copy
    the stored end-pressure slot. Temperature and derivative histories reset
    separately during native initialization. Intake flow feedback persists.
    """
    if type(knot_index) is not int or not 0 <= knot_index < 19:
        raise ValueError('invalid dyno knot index')
    previous, end = _stored_inputs(preceding_pressure, stored_end_pressure)
    return _f32(44.1) if knot_index == 0 else previous if knot_index == 1 else end
