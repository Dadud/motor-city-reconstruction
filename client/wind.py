"""Recovered track/time wind producer, original 0x536fb0.

The mode query, track vector, counter, seed and body transform are explicit
observations. Their game-level producers remain outside this calculation.
"""
from dataclasses import dataclass
import math
from client.tire_response import f32

TAU = 6.2831854820251465
INV_TAU = 0.15915493667125702


@dataclass(frozen=True)
class WindState:
    simulation_counter: int
    weather_seed: int
    track_direction: tuple
    world_to_body: tuple
    disabled: bool = False


@dataclass(frozen=True)
class WindOutput:
    body_velocity: tuple
    present: bool


def signed_remainder(value, divisor):
    return value % divisor if value >= 0 else -((-value) % divisor)


def calculate_wind(state):
    for value in (state.simulation_counter, state.weather_seed):
        if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
            raise ValueError('signed 32-bit counter and weather seed required')
    if type(state.disabled) is not bool:
        raise ValueError('boolean mode query observation required')
    if len(state.track_direction) != 3 or len(state.world_to_body) != 9:
        raise ValueError('track direction and row-vector matrix required')
    direction = tuple(map(f32, state.track_direction))
    matrix = tuple(map(f32, state.world_to_body))
    if state.disabled:
        return WindOutput((0., 0., 0.), False)
    time = f32(state.simulation_counter * .015625)
    first_phase = f32(time * f32(.033333335))
    second_phase = f32(time * f32(.026666667))
    first_sine = math.sin(first_phase * TAU)
    second_sine = f32(math.sin(second_phase * TAU))
    offset = f32(signed_remainder(state.weather_seed, 360) * f32(.0027777778))
    angle = f32(math.atan2(direction[0], direction[2]) * INV_TAU + offset)
    angle = f32(first_sine * second_sine * f32(.055555556) + angle)
    base = max(3, min(15, signed_remainder(state.weather_seed, 15)))
    magnitude = f32(base * f32(.44703) + first_sine * second_sine * f32(1.117575))
    x = f32(math.sin(angle * TAU) * magnitude)
    z = f32(math.cos(angle * TAU) * magnitude)
    body = tuple(f32((x * matrix[i] + 0. * matrix[i+3]) + z * matrix[i+6]) for i in range(3))
    return WindOutput(body, magnitude != 0.)
