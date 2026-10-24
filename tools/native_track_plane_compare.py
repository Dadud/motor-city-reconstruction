"""Compare the native track plane reconstruction with the Python port."""
import json
import random
import struct
import subprocess

from client.track_plane import track_plane


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def f32(value):
    return struct.unpack('<f', struct.pack('<I', value))[0]


def verify(runner, cases=512):
    rng=random.Random(0x42DC50)
    corpus=[]
    for _ in range(cases):
        vertices=((0.,0.,0.),(0.,0.,10.),(10.,rng.uniform(-3,3),10.),(10.,rng.uniform(-3,3),0.))
        vertices=tuple(tuple(f32(bits(v)) for v in point) for point in vertices)
        x,z=rng.randint(-2,12),rng.randint(-2,12)
        reference,normal=track_plane(x,z,vertices)
        values=[1,bits(x),bits(z),0,*[bits(v) for v in (0.,0.,0.)],
                *[bits(v) for point in vertices for v in point]]
        corpus.append((values,(True,reference,normal)))
    for _ in range(cases):
        row=tuple(f32(bits(rng.uniform(-50,50))) for _ in range(3))
        seed=tuple(f32(bits(rng.uniform(-1,1))) for _ in range(3))
        values=[0,bits(0),bits(0),0,*[bits(v) for v in seed],*[bits(v) for v in row]]
        corpus.append((values,(False,row,seed)))
    payload='\n'.join('0 '+' '.join(map(str,values)) for values,_ in corpus)+'\n'
    result=subprocess.run([str(runner)],input=payload,capture_output=True,text=True,check=True,timeout=30)
    rows=result.stdout.splitlines()
    if len(rows)!=len(corpus):raise AssertionError(('output rows',len(rows),len(corpus)))
    max_error=0.
    for case,(line,(_,expected)) in enumerate(zip(rows,corpus)):
        values=list(map(int,line.split()))
        written,reference,normal=expected
        if len(values)!=7 or values[0]!=int(written):raise AssertionError(('shape/mode',case,values))
        actual_reference=tuple(f32(v) for v in values[1:4])
        actual_normal=tuple(f32(v) for v in values[4:7])
        if actual_reference!=reference:raise AssertionError(('reference',case,actual_reference,reference))
        for axis,(actual,want) in enumerate(zip(actual_normal,normal)):
            error=abs(actual-want);max_error=max(max_error,error)
            if error>2e-7:raise AssertionError(('normal',case,axis,actual,want,error))
    return {'triangle_cases':cases,'row_cases':cases,'reference_points':'exact',
            'maximum_normal_absolute_error':max_error,
            'scope':'native triangle plane and explicit row-mode normal seed; lookup and caller state remain separate'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner');parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args();print(json.dumps(verify(args.runner,args.cases)))
