"""Native/Python comparison of the original-verified brake thermal matrix."""
import argparse
import json
import subprocess

from client.brake_thermal import update_brake_thermal
from client.tire_response import f32
from tools.brake_thermal_oracle import cases


def verify(runner):
    lines,expected=[],[]
    for s in cases():
        values=[s.service_control,int(s.parking_control),s.speed,s.mass_parameter,s.elevation_parameter,
            int(s.environment_flag),s.environment_code]
        for a in (s.front,s.rear):values.extend((a.temperature,a.diameter,a.cooling_coefficient,a.heat_capacity_factor,
            a.thermal_mass,a.temperature_limit,a.material_code,a.construction_code,a.countdown))
        for w in s.wheels:values.extend((w.brake_force,w.spin_scale,w.spin_value))
        lines.append(' '.join(format(v,'.17g') for v in values))
        r=update_brake_thermal(s)
        expected.append((r.front.temperature,r.rear.temperature,r.front.countdown,r.rear.countdown,
            r.kinetic_value,r.elevation_value,*(w.brake_force for w in r.wheels)))
    p=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    output=p.stdout.splitlines()
    if len(output)!=len(expected):raise AssertionError('native thermal output count mismatch')
    maximum=0
    for i,(line,target) in enumerate(zip(output,expected)):
        actual=tuple(f32(float(v)) for v in line.split())
        if len(actual)!=10:raise AssertionError('native thermal output shape mismatch')
        for a,b in zip(actual,target):
            error=abs(a-b)
            if error>max(.0001,abs(b)*3e-7):raise AssertionError((i,a,b))
            maximum=max(maximum,error)
    return {'cases':len(expected),'maximum_absolute_error':maximum}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
