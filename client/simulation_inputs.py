"""Recovered stock-vehicle simulation inputs for comparison harnesses.

This gathers verified tyre, suspension and engine metadata without replacing
the prototype driving model or claiming a complete force integrator.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from client.motion import POSE_STEP, SIMULATION_STEP, SUPPORT_LOOKAHEAD


@dataclass(frozen=True)
class WheelSimulationInputs:
    tire_radius_m: float
    spring_rate: float
    shock_coefficient: float
    shock_length_m: float


@dataclass(frozen=True)
class VehicleSimulationInputs:
    vehicle_id: int
    wheelbase_m: float
    wheels: dict[str, WheelSimulationInputs]
    engine_mass_kg: float
    engine_bore_m: float
    simulation_step_s: float
    pose_step_s: float
    support_lookahead_s: float

    @property
    def tire_radii_m(self) -> dict[str, float]:
        return {key: wheel.tire_radius_m for key, wheel in self.wheels.items()}


def _wheelbase_from_rig(rig) -> float:
    front = sum(point[2] for point in rig.centers[:2]) / 2
    rear = sum(point[2] for point in rig.centers[2:]) / 2
    wheelbase = abs(front - rear)
    if not math.isfinite(wheelbase) or not 0.5 <= wheelbase <= 10:
        raise ValueError('unsupported wheelbase for simulation inputs')
    return wheelbase


def build_stock_simulation_inputs(catalogue, vehicle, rig) -> VehicleSimulationInputs:
    """Collect recovered per-wheel and engine inputs for a stock vehicle."""
    tires = catalogue.tire_dimensions(vehicle)
    suspension = catalogue.suspension(vehicle)
    engine = catalogue.engine_block(vehicle)
    wheels = {}
    for key in ('LF', 'RF', 'LR', 'RR'):
        spring, shock = suspension[key]
        wheels[key] = WheelSimulationInputs(
            tire_radius_m=tires[key].radius,
            spring_rate=spring.rate,
            shock_coefficient=shock.coefficient,
            shock_length_m=shock.length,
        )
    return VehicleSimulationInputs(
        vehicle_id=vehicle.branded_id,
        wheelbase_m=_wheelbase_from_rig(rig),
        wheels=wheels,
        engine_mass_kg=engine.mass,
        engine_bore_m=engine.bore_m,
        simulation_step_s=SIMULATION_STEP,
        pose_step_s=POSE_STEP,
        support_lookahead_s=SUPPORT_LOOKAHEAD,
    )

