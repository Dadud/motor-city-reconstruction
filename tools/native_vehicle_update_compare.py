"""Native/Python complete controller and exact ordered action comparison.

All child effects are supplied authored observations; no original binary required.
"""
import argparse
import itertools
import json
import math
import subprocess
from client.vehicle_update import update_vehicle
from tools.vehicle_update_oracle import cases,mutation_cases,connected_cases,SuppliedStages

SCALARS=('attitude','speed','alternate_speed','secondary_angle','turning_radius_y','turning_radius_x','inverse_mass','mass','gravity_force','lateral_contribution','longitudinal_contribution','front_lever','rear_lever','front_moment','rear_moment','body_moment','angular_scale','maximum_steering','front_grip_gate','rear_grip_gate')
VECTORS=('linear_velocity','angular_velocity','linear_acceleration','angular_acceleration','extra_acceleration','local_linear','local_angular','local_acceleration','local_angular_acceleration','to_local','to_world','surface_coefficients')
WHEEL=('primary_coefficient','secondary_coefficient','base_grip','quality','spin_scale','spin','projected_speed','local_lateral','phase','primary_angle','clear_reference','clear_threshold')

def numbers(s):
    result=[getattr(s,n) for n in SCALARS]
    for n in VECTORS:result.extend(getattr(s,n))
    for w in s.wheels:result.extend(getattr(w,n) for n in WHEEL);result.extend(w.force)
    return result

def integers(s):
    result=[s.active,s.tilted,s.flags,s.environment_mode,s.fallback_surface,s.support_count,s.orientation_disabled,s.grip_boost]
    for w in s.wheels:result.extend((w.contact,-1 if w.surface_record is None else w.surface_record,w.surface_class,w.wear_mode,w.tire_type))
    return result

def verify(runner):
    corpus=list(itertools.chain(cases(),mutation_cases(),connected_cases()));lines=[]
    for s,o,b in corpus:
        values=integers(s)+numbers(s);queries={k:v for k,v in o.items() if k!='mutations'};values.append(len(queries))
        for name,value in queries.items():
            items=value if isinstance(value,tuple) else (value,);values.extend((name,len(items),*items))
        mutations=[(stage,name,value) for stage,changes in o.get('mutations',{}).items() for name,value in changes];values.append(len(mutations))
        for stage,name,value in mutations:
            items=tuple(itertools.chain.from_iterable(value)) if name=='forces' else value if isinstance(value,tuple) else (value,)
            values.extend((stage,name,len(items),*items))
        lines.append(' '.join(v if isinstance(v,str) else format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('controller output count')
    maximum=0.
    for index,(line,(s,o,branch)) in enumerate(zip(output,corpus)):
        out=update_vehicle(s,SuppliedStages(o));tokens=line.split()
        if tokens.pop(0)!=branch or out.branch!=branch:raise AssertionError((index,'branch'))
        expected=integers(out.state);actual=list(map(int,tokens[:len(expected)]));del tokens[:len(expected)]
        if actual!=expected:raise AssertionError((index,'integer state',actual,expected))
        expected=numbers(out.state);actual=list(map(float,tokens[:len(expected)]));del tokens[:len(expected)]
        for i,(a,b) in enumerate(zip(actual,expected)):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.0005,abs(b)*4e-7):raise AssertionError((index,i,a,b,error))
            maximum=max(maximum,error)
        count=int(tokens.pop(0));calls=[(tokens[i*2],int(tokens[i*2+1])) for i in range(count)]
        if len(tokens)!=count*2 or calls!=[(c.stage,-1 if c.slot is None else c.slot) for c in out.calls]:raise AssertionError((index,'ordered calls'))
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'complete native/Python controller; supplied child effects and exact ordered calls'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
