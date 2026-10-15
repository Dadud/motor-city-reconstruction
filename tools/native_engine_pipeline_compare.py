"""Native/Python comparison of persistent connected engine pipeline ticks."""
import argparse
import itertools
import json
import math
import subprocess
from client.engine_pipeline import update_engine_pipeline
from tools.engine_pipeline_oracle import cases,mutation_cases,SuppliedPipelineStages
from tools.native_engine_torque_update_compare import STATE_INTS,RPM_INTS,RPM_FLOATS,STATE_FLOATS,CONFIG_INTS,CONFIG_FLOATS

EXTRA_INTS=('vehicle_flags','selector_index','control_gate','thermal_mode')
EXTRA_FLOATS=('override_value','motion_metric','thermal_engagement','auxiliary_capacity','condition','main_temperature','drive_scale','primary_drive','alternate_drive','third_temperature','gate_one','gate_two','request','rate_two','rate_one','shielding_one','shielding_two')
LINK_CONFIG_FLOATS=('thermal_gain','cooling_capacity','main_loss_coefficient','transfer_coefficient','reference','upgrade_cooling','upgrade_capacity')
def integers(s):return [*[getattr(s,n) for n in STATE_INTS],*[getattr(s.rpm_state,n) for n in RPM_INTS],*[getattr(s,n) for n in EXTRA_INTS],*s.activation_delays]
def numbers(s):return [*[getattr(s.rpm_state,n) for n in RPM_FLOATS],*[getattr(s,n) for n in STATE_FLOATS+EXTRA_FLOATS]]

def verify(runner):
    corpus=list(itertools.chain(cases(),mutation_cases()));lines=[]
    for s,c,o,ticks in corpus:
        values=[ticks]+integers(s)+numbers(s)+[getattr(c.torque,n) for n in CONFIG_INTS+CONFIG_FLOATS]+[getattr(c.links,n) for n in LINK_CONFIG_FLOATS]+[len(c.torque.torque_curve),*c.torque.torque_curve,len(c.links.mode_coefficients),*c.links.mode_coefficients]
        responses={k:v for k,v in o.items() if k!='mutations'};values.append(len(responses))
        for name,value in responses.items():values.extend((name,*(value if name=='boost' else (value,0))))
        mutations=[(domain,stage,n,v) for (domain,stage),changes in o.get('mutations',{}).items() for n,v in changes];values.append(len(mutations))
        for item in mutations:values.extend(item)
        lines.append(' '.join(v if isinstance(v,str) else format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30);output=result.stdout.splitlines()
    if len(output)!=sum(ticks for s,c,o,ticks in corpus):raise AssertionError('pipeline output count')
    maximum=0.;index=0
    def compare(a,b,name):
        nonlocal maximum
        error=abs(a-b)
        if not math.isfinite(a) or error>max(.0001,abs(b)*4e-7):raise AssertionError((index,name,a,b))
        maximum=max(maximum,error)
    for state,c,o,ticks in corpus:
        for tick in range(ticks):
            if tick:state.counter+=1
            expected=update_engine_pipeline(state,c,SuppliedPipelineStages(o));tokens=output[index].split();ints=integers(expected.state)
            if list(map(int,tokens[:len(ints)]))!=ints:raise AssertionError((index,'integer state',tokens[:len(ints)],ints))
            del tokens[:len(ints)]
            for n,value in enumerate(numbers(expected.state)):compare(float(tokens.pop(0)),value,n)
            count=int(tokens.pop(0))
            if count!=len(expected.calls):raise AssertionError((index,'action count'))
            for action in expected.calls:
                domain=tokens.pop(0);stage=tokens.pop(0);code=int(tokens.pop(0));n=int(tokens.pop(0))
                if domain!=action.domain or stage!=action.stage or code!=(-1 if action.code is None else action.code) or n!=len(action.values):raise AssertionError((index,'action identity'))
                for value in action.values:compare(float(tokens.pop(0)),value,'action value')
            if tokens:raise AssertionError((index,'unexpected output'))
            state=expected.state;index+=1
    return {'scenarios':len(corpus),'ticks':index,'maximum_absolute_error':maximum,'scope':'native/Python persistent shared-owner engine pipeline; exact nested order and explicit external boundaries'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
