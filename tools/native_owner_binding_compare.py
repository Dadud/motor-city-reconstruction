"""Bit-exact native/Python owner binding comparisons using the original oracle corpus."""
import argparse
import itertools
import json
import struct
import subprocess
from client.owner_binding import bind_owner_inertia,bind_axle_levers,bind_startup_com,body_inertia_scales


def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner):
    lines=[];expected=[]
    def case(mode,shape,inputs,outputs):
        lines.append(' '.join(map(str,(mode,shape,*(bits(v) for v in inputs)))))
        expected.append(tuple(map(bits,outputs)))
    for mass,extent,shape in itertools.product((0.,575.,998.125,1800.25),
            ((.7,.6,1.8),(.7112,.5334,1.346),(.1234567,1.234567,3.456789)),range(-1,9)):
        r=bind_owner_inertia(mass,extent,shape)
        case(0,shape,(mass,*extent),(r.mass,r.inverse_mass,*r.half_extents,*r.shape_scales,*r.inertia,*r.inverse_inertia))
    for wheelbase,fraction in itertools.product((.5,2.692,4.1234567),(-.1,0.,.4305,.5,1.,1.1)):
        r=bind_axle_levers(wheelbase,fraction);case(1,0,(wheelbase,fraction),(r.front,r.rear))
    for values in itertools.product((.5334,1.),(.5,.8),(-1.2,1.346),(.5,1.532)):
        r=bind_startup_com(*values);case(2,0,values,(r.vertical,r.longitudinal))
    for shape in range(-2,11):
        for initial in ((1.,1.,1.),(.1234567,-.7654321,-0.)):
            case(3,shape,initial,body_inertia_scales(shape,initial))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if observed!=expected:raise AssertionError('native owner binding differs')
    return dict(cases=len(lines),maximum_absolute_error=0,scope='native/Python mass, inertia, levers, COM and prior scale preservation; output bits exact')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
