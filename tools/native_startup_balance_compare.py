"""Native/Python complete startup load and balance coefficient comparisons."""
import argparse
import json
import itertools
import struct
import subprocess
from client.startup_balance import startup_load_coefficient,startup_balance_coefficient,startup_brake_balance,brake_diameter,brake_capacity
from tools.startup_balance_oracle import cases


def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner):
    lines=[];expected=[]
    for config in cases():
        for alternate in (False,True):
            lines.append(' '.join(map(str,(0,int(alternate),*struct.unpack('<520I',config)))))
            expected.append((bits(startup_load_coefficient(config)),bits(startup_balance_coefficient(config,alternate_load=alternate)),bits(startup_brake_balance(config))))
    count=len(lines)
    for code in (*range(23),0xffffffff):
        lines.append(f'1 {code}');expected.append((bits(brake_diameter(code)),))
    for diameter,material,construction,pressure,auxiliary in itertools.product((.2032,.3175,.4572),range(4),range(3),(.25,1.),(False,True)):
        lines.append(' '.join(map(str,(2,bits(diameter),material,construction,bits(pressure),int(auxiliary)))))
        expected.append(struct.unpack('<Q',struct.pack('<d',brake_capacity(diameter,material,construction,pressure,auxiliary))))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if observed!=expected:
        raise AssertionError([(i,a,b) for i,(a,b) in enumerate(zip(observed,expected)) if a!=b][:8])
    return dict(configuration_cases=count,helper_cases=len(lines)-count,maximum_absolute_error=0,
        scope='native/Python complete startup load, balance and brake coefficients; float32 and float64 output bits exact')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
