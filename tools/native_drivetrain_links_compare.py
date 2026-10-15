"""Native/Python condition links comparison using original-verified scenarios."""
import argparse
import itertools
import json
import math
import subprocess
from client.drivetrain_links import *
from tools.drivetrain_links_oracle import cases,mutation_cases,SuppliedLinkEffects

STATE_INTS=('engine_flags','vehicle_flags','rpm','mode','alternate_enabled','bypass')
STATE_FLOATS=('speed','normalized_rpm','engagement','auxiliary_temperature','auxiliary_capacity','condition','main_temperature','loss','drive_scale','primary_drive','alternate_drive','third_temperature','gate_one','gate_two','threshold_observation','request','rate_two','rate_one','shielding_one','shielding_two')
CONFIG_INTEGERS=('material_index','durability_index','loss_index','third_enabled')
CONFIG_FLOATS=('alternate_threshold','thermal_gain','cooling_capacity','main_loss_coefficient','transfer_coefficient','reference','upgrade_enabled','upgrade_cooling','upgrade_capacity')

def verify(runner):
    corpus=list(itertools.chain(cases(),mutation_cases()));lines=[]
    for kind,s,c,m in corpus:
        values=[kind,*[getattr(s,n) for n in STATE_INTS+STATE_FLOATS],*[getattr(c,n) for n in CONFIG_INTEGERS+CONFIG_FLOATS],len(c.mode_coefficients),*c.mode_coefficients]
        mutations=[(code,n,v) for code,changes in m.items() for n,v in changes];values.append(len(mutations))
        for item in mutations:values.extend(item)
        lines.append(' '.join(v if isinstance(v,str) else format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30);output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('condition output count')
    maximum=0.
    def compare(a,b,i,name):
        nonlocal maximum
        error=abs(a-b)
        if not math.isfinite(a) or error>max(.00003,abs(b)*4e-7):raise AssertionError((i,name,a,b))
        maximum=max(maximum,error)
    for i,(line,(kind,s,c,m)) in enumerate(zip(output,corpus)):
        expected=(update_gear_link if kind=='gear' else update_drivetrain_loads)(s,c,SuppliedLinkEffects(m));tokens=line.split()
        for name in STATE_INTS:
            if int(tokens.pop(0))!=getattr(expected.state,name):raise AssertionError((i,name))
        for name in STATE_FLOATS:compare(float(tokens.pop(0)),getattr(expected.state,name),i,name)
        count=int(tokens.pop(0))
        if count!=len(expected.calls):raise AssertionError((i,'action count'))
        for action in expected.calls:
            stage=tokens.pop(0);code=int(tokens.pop(0));n=int(tokens.pop(0))
            if stage!=action.stage or code!=action.code or n!=len(action.values):raise AssertionError((i,'action identity'))
            for value in action.values:compare(float(tokens.pop(0)),value,i,'action argument')
        if tokens:raise AssertionError((i,'unexpected output'))
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python full condition and thermal bodies with explicit supplied damage/effect consumers'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
