"""Compare native engine dispatch against the original-verified Python corpus."""
import argparse
import json
import math
import subprocess
from client.engine_update import update_engine
from tools import engine_update_oracle as oracle

RPM_INTS=('idle_rpm','configured_max_rpm','target_rpm','rpm','limiter_rpm','gear_index','enabled')
RPM_FLOATS=('throttle','normalized_rpm','inertia_factor','acceleration_input','angular_speed','gear_speed_factor','longitudinal_speed','acceleration_output')
FLOATS=('override_value','motion_metric','effective_torque','curve_torque','power','engagement')

def integers(s):
    return [s.engine_flags,s.vehicle_flags,s.selector_index,s.current_counter,s.control_gate,*s.activation_delays,*[getattr(s.rpm_state,n) for n in RPM_INTS]]

def numbers(s):
    return [*[getattr(s.rpm_state,n) for n in RPM_FLOATS],*[getattr(s,n) for n in FLOATS]]

def state_values(s):return integers(s)+numbers(s)+[len(s.torque_curve),*s.torque_curve]

def verify(runner):
    corpus=list(oracle.cases())+list(getattr(oracle,'mutation_cases',lambda:())());lines=[]
    for s,o in corpus:
        values=state_values(s);observations={k:v for k,v in o.items() if k!='mutations'}
        values.append(len(observations))
        for k,v in observations.items():values.extend((k,v))
        mutations=[]
        for stage,changes in o.get('mutations',{}).items():
            for name,value in (changes.items() if isinstance(changes,dict) else changes):mutations.append((stage,name,value))
        values.append(len(mutations))
        for m in mutations:values.extend(m)
        lines.append(' '.join(v if isinstance(v,str) else format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('engine output count')
    maximum=0.
    for i,(line,(s,o)) in enumerate(zip(output,corpus)):
        out=update_engine(s,oracle.SuppliedEngineStages(o));tokens=line.split()
        expected=integers(out.state);actual=list(map(int,tokens[:len(expected)]));del tokens[:len(expected)]
        if actual!=expected:raise AssertionError((i,'integer state',actual,expected))
        expected=numbers(out.state);actual=list(map(float,tokens[:len(expected)]));del tokens[:len(expected)]
        for j,(a,b) in enumerate(zip(actual,expected)):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.00025,abs(b)*3e-7):raise AssertionError((i,j,a,b,error))
            maximum=max(maximum,error)
        n=int(tokens.pop(0));curve=list(map(float,tokens[:n]));del tokens[:n]
        if curve!=list(out.state.torque_curve):raise AssertionError((i,'curve mutation'))
        n=int(tokens.pop(0));calls=[(tokens[j*2],int(tokens[j*2+1])) for j in range(n)]
        if len(tokens)!=n*2 or calls!=[(c.stage,-1 if c.argument is None else c.argument) for c in out.calls]:raise AssertionError((i,'ordered calls',calls,out.calls))
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python full dispatcher with recovered RPM and curve; explicit supplied children'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
