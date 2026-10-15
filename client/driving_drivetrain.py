"""Bind the five recovered drivetrain children to one shared driving owner."""
from dataclasses import replace
from client.drivetrain_stages import (DriveState,DriveConfig,update_clutch,prepare_drive,
    accumulate_drive_request,distribute_drive,apply_drive_forces)


class DrivingDrivetrain:
    """Use as DrivingEngine.execute, keeping extra mechanical fields persistent.

    effects(action, drive_state, engine, controller, force_inputs) must supply
    component effects and per-wheel vehicle gates. During these callbacks change
    drive aliases through drive_state. external(action,engine,controller,inputs)
    handles remaining engine children. Both callbacks are required.
    """
    methods={'engine_setup':update_clutch,'engine_control':prepare_drive,
        'engagement_inputs':accumulate_drive_request,'wheel_drive':distribute_drive,
        'engine_finalize':apply_drive_forces}

    def __init__(self,state,config,controls,loads,brakes,effects,external):
        if not isinstance(state,DriveState) or not isinstance(config,DriveConfig) or not callable(effects) or not callable(external):
            raise ValueError('explicit drivetrain state/configuration and remaining effects required')
        self.state,self.config,self.controls,self.loads,self.brakes=state,config,controls,loads,brakes
        self.effects,self.external,self.calls=effects,external,()

    def _read(self,e,s,f):
        d=self.state;r=e.rpm_state
        for name in ('engine_flags','vehicle_flags','engagement','coupling_resistance',
                     'effective_torque','drag_speed','bypass','request'):
            setattr(d,name,getattr(e,name))
        d.rpm,d.gear,d.angular_speed,d.throttle=r.rpm,r.gear_index,r.angular_speed,r.throttle
        d.longitudinal_speed,d.speed=r.longitudinal_speed,e.effect_motion
        d.acceleration,d.alternate_speed,d.component_mode=s.local_acceleration[2],s.alternate_speed,s.fallback_surface
        d.override_byte=int(f.spin.override_control);d.raw_throttle=self.controls.controls.throttle
        d.wheels=[replace(old,spin=w.spin,adjustment=spin.spin_adjustment,radius=w.spin_scale,
            inertia=spin.kinetic_parameter,normal_load=w.force[1],longitudinal_force=w.force[2],
            driven=spin.correction_enabled,contact=w.contact) for old,w,spin in zip(d.wheels,s.wheels,f.spin.wheels)]

    def _publish(self,d,e,s,f):
        for name in ('engine_flags','vehicle_flags','engagement','coupling_resistance',
                     'effective_torque','drag_speed','bypass','request'):
            setattr(e,name,getattr(d,name))
        e.rpm_state=replace(e.rpm_state,rpm=d.rpm,gear_index=d.gear,angular_speed=d.angular_speed,
            throttle=d.throttle,longitudinal_speed=d.longitudinal_speed)
        e.effect_motion=d.speed
        s.flags,s.speed,s.alternate_speed,s.fallback_surface=d.vehicle_flags,d.speed,d.alternate_speed,d.component_mode
        s.local_acceleration=(*s.local_acceleration[:2],d.acceleration)
        s.local_linear=(*s.local_linear[:2],d.longitudinal_speed)
        self.controls.controls.flags=d.engine_flags;self.controls.controls.throttle=d.raw_throttle
        f.other_control=d.throttle;f.spin=replace(f.spin,rpm=d.rpm,override_control=d.override_byte==1,
            wheels=tuple(replace(old,spin_adjustment=w.adjustment,kinetic_parameter=w.inertia,
                correction_enabled=w.driven) for old,w in zip(f.spin.wheels,d.wheels)))
        for w,drive in zip(s.wheels,d.wheels):
            w.spin,w.spin_scale,w.contact=drive.spin,drive.radius,drive.contact
            w.force=(w.force[0],drive.normal_load,drive.longitudinal_force)
        # Original +0xac distribution also supplies brake coupling inertia.
        self.brakes.state=replace(self.brakes.state,wheels=tuple(replace(old,inertia_multiplier=w.distribution)
            for old,w in zip(self.brakes.state.wheels,d.wheels)))
        self.brakes.drive_factors=self.config.inertia_factors
        selected=f.spin.direction_mode
        if not 0<=selected<min(len(self.config.gear_ratios),len(self.config.speed_factors)):
            raise ValueError('selected gear requires shared mechanical table entries')
        self.loads.gear_factor=self.config.gear_ratios[selected]
        f.spin=replace(f.spin,gear_multiplier=self.config.speed_factors[selected])

    def __call__(self,action,e,s,f):
        if action.domain!='dispatch' or action.stage not in self.methods:
            return self.external(action,e,s,f)
        if self.config.maximum_rpm!=e.rpm_state.configured_max_rpm:
            raise ValueError('inconsistent shared configured maximum RPM')
        self._read(e,s,f);calls=[]
        def execute(call,d):
            self._publish(d,e,s,f);calls.append(call)
            result=self.effects(call,d,e,s,f)
            self._publish(d,e,s,f);return result
        method=self.methods[action.stage]
        self.state=method(self.state,self.config,execute) if action.stage in ('wheel_drive','engine_finalize') else method(self.state,self.config)
        self.calls=(*self.calls,*calls)
        self._publish(self.state,e,s,f)
