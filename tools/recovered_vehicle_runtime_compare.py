"""Cross-check the authored native session composition against recovered Python bodies.

Synthetic query responses/forces are fixtures, not stock or live behavior.
The underlying body oracles separately execute original instructions.
"""
import argparse
from dataclasses import replace
import math
import subprocess
from client.vehicle_update import VehicleUpdateState, update_vehicle, apply_linear_update
from client.engine_pipeline import update_engine_pipeline
from tools.engine_pipeline_oracle import base


def verify(runner):
    # Retain the same verified engine fixture/configuration as its own oracle.
    engine, config = base()
    vehicle = VehicleUpdateState(flags=4, linear_velocity=(1.,0.,20.),
        local_linear=(1.,0.,20.), alternate_speed=12.)
    result = subprocess.run([str(runner)], text=True, capture_output=True, check=True, timeout=30)
    lines = result.stdout.splitlines()
    assert len(lines) == 120
    maximum = 0.
    for tick, line in enumerate(lines):
        engine_calls = []
        def execute(a, v):
            nonlocal engine
            if a.stage == 'linear_update':
                apply_linear_update(v, tick % 7 != 0)
                return 0.
            if a.stage == 'engine':
                engine.vehicle_flags = v.flags
                engine.effect_motion = v.speed
                engine.rpm_state = replace(engine.rpm_state, longitudinal_speed=v.local_linear[2])
                def publish(e):
                    v.flags, v.speed = e.vehicle_flags, e.effect_motion
                    v.local_linear = (*v.local_linear[:2], e.rpm_state.longitudinal_speed)
                def child(call, e):
                    publish(e)
                    if call.stage == 'engine_finalize':
                        e.effect_motion += .25
                    publish(e)
                    return (10000 if call.stage == 'rpm_limit' else 0)
                out = update_engine_pipeline(engine, config, child)
                engine = out.state
                engine_calls.extend(out.calls)
                publish(engine)
                return 0.
            if a.stage == 'global_mode':
                return float(tick % 3 == 0)
            if a.stage == 'predict_support':
                for w in v.wheels: w.contact = tick % 5 != 0
            if a.stage == 'tires':
                for w in v.wheels: w.force = (0.,2500.,150.)
            return float(a.stage == 'vehicle_gate')
        out = update_vehicle(vehicle, execute)
        vehicle = out.state
        actual = line.split()
        expected = [out.branch, len(out.calls),len(engine_calls),vehicle.flags,vehicle.speed,
            *vehicle.linear_velocity,vehicle.local_linear[2],engine.rpm_state.rpm,
            engine.main_temperature,engine.effective_torque]
        for i,(a,b) in enumerate(zip(actual,expected,strict=True)):
            if isinstance(b,str): assert a == b,(tick,i,a,b)
            else:
                error=abs(float(a)-b)
                assert math.isfinite(float(a)) and error <= max(.0001, abs(b)*4e-7),(tick,i,a,b)
                maximum=max(maximum,error)
    return {'ticks':120,'maximum_absolute_error':maximum,
        'scope':'synthetic multi-frame native/Python vehicle+engine composition; not live gameplay'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runner')
    print(verify(p.parse_args().runner))
