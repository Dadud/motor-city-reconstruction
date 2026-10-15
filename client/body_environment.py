"""Connected original environment producers and body-resistance calculation."""
from dataclasses import dataclass, replace
from client.air_density import calculate_air_density
from client.wind import WindState, WindOutput, calculate_wind
from client.drafting import DraftingOutput, calculate_drafting
from client.body_resistance import BodyResistanceState, BodyResistanceOutput, calculate_body_resistance


@dataclass(frozen=True)
class BodyEnvironment:
    altitude: float
    cold_environment: bool
    weather_enabled: bool
    weather_code: int
    wind: WindState
    current_vehicle: int
    vehicles: tuple


@dataclass(frozen=True)
class BodyEnvironmentOutput:
    body: BodyResistanceOutput
    density: float
    wind: WindOutput
    drafting: DraftingOutput


def calculate_body_environment(body: BodyResistanceState, environment: BodyEnvironment):
    """Original 536480 producer order with stored float32 handoffs.

    Track, counter/mode, vehicle geometry and component fields are explicit
    observations. Returned drafting state includes writes to the selected peer;
    the caller must retain those records for later stages.
    """
    density = calculate_air_density(environment.altitude, environment.cold_environment,
                                    environment.weather_enabled, environment.weather_code)
    wind = calculate_wind(environment.wind)
    drafting = calculate_drafting(environment.current_vehicle, environment.vehicles)
    state = replace(body, density=density, wind_lateral=wind.body_velocity[0],
                    wind_longitudinal=wind.body_velocity[2], drafting_factor=drafting.factor)
    return BodyEnvironmentOutput(calculate_body_resistance(state), density, wind, drafting)
