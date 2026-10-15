"""Compare native complete torque update to the original-verified Python corpus."""
import argparse
import itertools
import json
import math
import subprocess
from client.engine_torque_update import update_engine_torque
from tools.engine_torque_update_oracle import cases,mutation_cases,SuppliedTorqueStages

STATE_INTS=('engine_flags','bypass','counter','alternate_enabled','boost_flag','environment_override','environment_selector_enabled','environment_selector')
RPM_INTS=('idle_rpm','configured_max_rpm','target_rpm','rpm','limiter_rpm','gear_index','enabled')
RPM_FLOATS=('throttle','normalized_rpm','inertia_factor','acceleration_input','angular_speed','gear_speed_factor','longitudinal_speed','acceleration_output')
STATE_FLOATS=('curve_torque','effective_torque','power','engagement','brake_control','condition_accumulator','condition_gate','damage_d3c','damage_d40','damage_d44','damage_d48','damage_d4c','loss','auxiliary_temperature','boost_observation','effect_motion','drag_factor','drag_speed','drag','coupling_resistance','environment_field')
CONFIG_INTS=('third_enabled','loss_index','material_index','upgrade_index','gain_mode','durability_index','limit_a','limit_b','overspeed_base','overspeed_extra','overload_index')
CONFIG_FLOATS=('upgrade_enabled','boost_threshold','boost_available','exhaust_tag','compression','overload_coefficient','torque_capacity')
def integers(s):return [*[getattr(s,n) for n in STATE_INTS],*[getattr(s.rpm_state,n) for n in RPM_INTS]]
def numbers(s):return [*[getattr(s.rpm_state,n) for n in RPM_FLOATS],*[getattr(s,n) for n in STATE_FLOATS]]

def verify(runner):
    corpus=list(itertools.chain(cases(),mutation_cases()));lines=[]
    for s,c,o in corpus:
        values=integers(s)+numbers(s)+[getattr(c,n) for n in CONFIG_INTS+CONFIG_FLOATS]+[len(c.torque_curve),*c.torque_curve]
        responses={k:v for k,v in o.items() if k!='mutations'};values.append(len(responses))
        for name,value in responses.items():values.extend((name,*(value if name=='boost' else (value,0))))
        mutations=[(stage,n,v) for stage,changes in o.get('mutations',{}).items() for n,v in changes];values.append(len(mutations))
        for item in mutations:values.extend(item)
        lines.append(' '.join(v if isinstance(v,str) else format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30);output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('torque output count')
    maximum=0.
    def compare(a,b,i,name):
        nonlocal maximum
        error=abs(a-b)
        if not math.isfinite(a) or error>max(.0001,abs(b)*4e-7):raise AssertionError((i,name,a,b))
        maximum=max(maximum,error)
    for i,(line,(s,c,o)) in enumerate(zip(output,corpus)):
        expected=update_engine_torque(s,c,SuppliedTorqueStages(o));tokens=line.split();ints=integers(expected.state)
        if list(map(int,tokens[:len(ints)]))!=ints:raise AssertionError((i,'integer outputs',tokens[:len(ints)],ints))
        del tokens[:len(ints)]
        for n,value in enumerate(numbers(expected.state)):compare(float(tokens.pop(0)),value,i,n)
        count=int(tokens.pop(0))
        if count!=len(expected.calls):raise AssertionError((i,'action count'))
        for action in expected.calls:
            stage=tokens.pop(0);code=int(tokens.pop(0));n=int(tokens.pop(0))
            if stage!=action.stage or code!=(-1 if action.code is None else action.code) or n!=len(action.values):raise AssertionError((i,'action identity'))
            for value in action.values:compare(float(tokens.pop(0)),value,i,'action value')
        if tokens:raise AssertionError((i,'unexpected output'))
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python complete torque update; explicit supplied producer/effect boundaries'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
