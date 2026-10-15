"""Shared-owner bridge from the vehicle controller to recovered engine bodies."""
from dataclasses import replace
from client.engine_pipeline import EnginePipelineState, EnginePipelineConfig, update_engine_pipeline
from client.driving_controls import DrivingControls
from client.driving_loads import LoadParameters
from client.driving_environment import EnvironmentInputs


class DrivingEngine:
    """Wrap the control/load/environment executor, retaining engine state.

    execute(action, engine, controller, force_inputs) supplies unrecovered engine
    children. Shared fields are published before each callback. Change shared
    aliases through the mutable engine argument; controller/force writes are for
    their other fields. Setup, clutch and wheel-drive behavior remain mandatory.
    The engine's +0xb54 RPM gear index differs from the +0xa69 selected gear byte.
    """
    stages = frozenset(('engine',))

    def __init__(self, state, config, controls, loads, environment, execute, external):
        if not (isinstance(state, EnginePipelineState) and isinstance(config, EnginePipelineConfig)
                and isinstance(controls, DrivingControls) and isinstance(loads, LoadParameters)
                and isinstance(environment, EnvironmentInputs)
                and callable(execute) and callable(external)):
            raise ValueError('explicit engine state, shared contexts and child executors required')
        if bool(config.torque.third_enabled) != controls.controls.assisted_gears:
            raise ValueError('inconsistent shared configuration +0x68c')
        self.state, self.config, self.controls = state, config, controls
        self.loads, self.environment = loads, environment
        self.execute, self.external, self.calls = execute, external, ()

    def _read_shared(self, s, f):
        e, env = self.state, self.environment.environment
        e.vehicle_flags = s.flags
        e.engine_flags = self.controls.controls.flags
        e.rpm_state = replace(e.rpm_state, rpm=f.spin.rpm,
            longitudinal_speed=s.local_linear[2], throttle=f.other_control)
        e.brake_control, e.thermal_mode = f.service_control, f.spin.direction_mode
        e.curve_torque, e.effect_motion = self.loads.torque, s.speed
        e.environment_field = env.altitude
        e.environment_override, e.environment_selector_enabled = env.cold_environment, env.weather_enabled
        e.environment_selector, e.counter = env.weather_code, env.wind.simulation_counter

    def _publish(self, e, s, f):
        s.flags, s.speed = e.vehicle_flags, e.effect_motion
        s.local_linear = (*s.local_linear[:2], e.rpm_state.longitudinal_speed)
        self.controls.controls.flags = e.engine_flags
        self.controls.controls.output_gear = e.thermal_mode
        self.controls.controls.brake_output = e.brake_control
        self.controls.controls.throttle_output = e.rpm_state.throttle
        f.spin = replace(f.spin, rpm=e.rpm_state.rpm, direction_mode=e.thermal_mode)
        f.service_control, f.other_control = e.brake_control, e.rpm_state.throttle
        self.loads.torque = e.curve_torque
        env = self.environment.environment
        self.environment.environment = replace(env, altitude=e.environment_field,
            cold_environment=e.environment_override, weather_enabled=e.environment_selector_enabled,
            weather_code=e.environment_selector,
            wind=replace(env.wind, simulation_counter=e.counter))

    def __call__(self, call, s, force):
        if call.stage != 'engine':
            return self.external(call, s, force)
        self._read_shared(s, force)
        def execute(action, engine):
            self._publish(engine, s, force)
            result = self.execute(action, engine, s, force)
            self._publish(engine, s, force)
            return result
        out = update_engine_pipeline(self.state, self.config, execute)
        self.state, self.calls = out.state, out.calls
        self._publish(out.state, s, force)
