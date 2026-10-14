"""Native/Python complete numeric brake and ordered effect-call comparison."""
import argparse
import json
import math
import subprocess
from client.brake_forces import update_brake_forces
from tools.brake_forces_oracle import cases


def verify(runner):
    corpus=list(cases());lines=[]
    for s in corpus:
        t=s.thermal
        values=[t.service_control,int(t.parking_control),t.speed,t.mass_parameter,t.elevation_parameter,
            int(t.environment_flag),t.environment_code]
        for a in (t.front,t.rear):values.extend((a.temperature,a.diameter,a.cooling_coefficient,a.heat_capacity_factor,
            a.thermal_mass,a.temperature_limit,a.material_code,a.construction_code,a.countdown))
        for w in t.wheels:values.extend((w.brake_force,w.spin_scale,w.spin_value))
        values.extend((s.front_quality,s.rear_quality,s.front_gate,s.rear_gate,s.rear_distribution,
            s.drive_factor,s.pitch_angle,s.vehicle_code,int(s.auxiliary_flag),s.parking_ramp))
        for w in s.wheels:values.extend((w.spin_value,w.spin_adjustment,w.spin_scale,w.projected_speed,w.normal_load,
            w.longitudinal_force,w.control_angle,w.component_code,w.inertia_addend,w.inertia_multiplier))
        lines.append(' '.join(format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('brake output count differs')
    maximum=0.0
    for index,(line,s) in enumerate(zip(output,corpus)):
        r=update_brake_forces(s);out=r.state;t=out.thermal
        expected=[t.front.temperature,t.rear.temperature,t.front.countdown,t.rear.countdown,
            t.kinetic_value,t.elevation_value,out.parking_ramp]
        for i,w in enumerate(out.wheels):expected.extend((w.spin_adjustment,w.longitudinal_force,t.wheels[i].brake_force))
        expected.append(len(r.wear_events))
        for slot,amount in r.wear_events:expected.extend((slot,amount))
        expected.append(len(r.controller_events));expected.extend(r.controller_events)
        actual=list(map(float,line.split()))
        if len(actual)!=len(expected):raise AssertionError('brake output shape differs')
        for field,(a,b) in enumerate(zip(actual,expected)):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.0005,abs(b)*3e-7):raise AssertionError((index,field,a,b,error))
            maximum=max(maximum,error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python complete numeric brake and effects'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
