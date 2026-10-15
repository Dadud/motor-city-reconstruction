"""Recovered brake/thermal stages consuming the shared driving owner."""
from dataclasses import replace
from client.brake_forces import BrakeForceState, update_brake_forces
from client.driving_controls import DrivingControls
from client.driving_loads import LoadParameters
from client.driving_environment import EnvironmentInputs


class DrivingBrakes:
    """Retain brake temperatures, force history and parking ramp across ticks.

    effects(events, controller, force_inputs, brake_state) is mandatory. Events
    preserve original wear/controller interleaving, but are delivered after the
    numeric stage. Mutations to observations inside the original wheel loop are
    not reproduced by this adapter. No component/hardware behavior is invented.
    """
    stages=frozenset(('brakes',))

    def __init__(self,state,drive_factors,controls,loads,environment,effects,external):
        if not (isinstance(state,BrakeForceState) and isinstance(controls,DrivingControls)
                and isinstance(loads,LoadParameters) and isinstance(environment,EnvironmentInputs)
                and callable(effects) and callable(external)):
            raise ValueError('explicit brake state, shared contexts and effect/child executors required')
        self.state,self.controls,self.loads,self.environment=state,controls,loads,environment
        self.drive_factors=tuple(drive_factors)
        self.effects,self.external,self.events=effects,external,()

    def __call__(self,call,s,f):
        if call.stage!='brakes':return self.external(call,s,f)
        if not 0<=f.spin.direction_mode<len(self.drive_factors):
            raise ValueError('brake inertia factor required for selected gear')
        env=self.environment.environment
        thermal=replace(self.state.thermal,service_control=f.service_control,parking_control=f.parking_control,
            speed=s.speed,mass_parameter=self.loads.configuration_mass,elevation_parameter=env.altitude,
            environment_flag=env.cold_environment,environment_code=env.weather_code if env.weather_enabled else 0)
        wheels=tuple(replace(old,spin_value=w.spin,spin_adjustment=spin.spin_adjustment,
            spin_scale=w.spin_scale,projected_speed=w.projected_speed,normal_load=w.force[1],
            longitudinal_force=w.force[2],control_angle=spin.slip_ratio,
            component_code=w.surface_class,inertia_addend=spin.kinetic_parameter)
            for old,w,spin in zip(self.state.wheels,s.wheels,f.spin.wheels))
        if any(len(wheels)!=4 for wheels in (self.state.wheels,s.wheels,f.spin.wheels)):
            raise ValueError('four shared brake wheel records required')
        self.last_input=replace(self.state,thermal=thermal,wheels=wheels,
            pitch_angle=self.loads.pitch,vehicle_code=s.environment_mode,
            drive_factor=self.drive_factors[f.spin.direction_mode],
            auxiliary_flag=bool(self.controls.controls.flags&0x20))
        out=update_brake_forces(self.last_input)
        self.state,self.events=out.state,out.events
        for w,brake in zip(s.wheels,out.state.wheels):
            w.force=(w.force[0],w.force[1],brake.longitudinal_force)
        f.spin=replace(f.spin,wheels=tuple(replace(spin,spin_adjustment=brake.spin_adjustment)
            for spin,brake in zip(f.spin.wheels,out.state.wheels)))
        self.effects(self.events,s,f,self.state)
