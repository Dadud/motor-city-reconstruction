"""Compare the full 0x474ee0 branch router with captured original callbacks."""
import argparse
import random
import struct

from client.render_quad_dispatch import dispatch_quad
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def _case(rng,index):
    vertices=[]
    for vertex in range(4):
        if index<256:
            code=(index+vertex*67)&0xff
        elif index<512:
            # Force each corner to be the only clipped vertex in turn.
            code=0 if vertex!=((index-256)%4) else 1<<((index//4)%6)
        else:
            code=rng.getrandbits(8)
        w=(_word(rng.choice((-1.,0.,.5,1.,2.))) if index%5==0 else
           rng.getrandbits(32))
        vertices.append((rng.getrandbits(32),rng.getrandbits(32),
            rng.getrandbits(32),w,rng.getrandbits(32),
            (rng.getrandbits(24)<<8)|code,rng.getrandbits(32),
            rng.getrandbits(32)))
    if index%13==0:
        vertex=index%4
        record=list(vertices[vertex]); record[0]=0xffc00000
        vertices[vertex]=tuple(record)
    return tuple(vertices)


def verify(executable,cases=1024):
    if type(cases) is not int or not 1<=cases<=20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x474ee0)
    oracle=DynoOracle(executable)
    for index in range(cases):
        vertices=_case(rng,index)
        trace=dispatch_quad(vertices)
        expected={'quad_callbacks':((trace.quad_callback,)
                                     if trace.quad_callback is not None else ()),
                  'triangle_callbacks':trace.triangle_callbacks,
                  'clip_calls':trace.clip_requests}
        actual=oracle.render_quad_routing(vertices)
        if actual!=expected:
            raise AssertionError(
                f'case {index}: codes={tuple(v[5]&0xff for v in vertices)!r}; '
                f'expected={expected!r}; actual={actual!r}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=1024)
    args=parser.parse_args()
    print(f'0x474ee0 routing matches {verify(args.executable,args.cases)} calls')


if __name__=='__main__':
    main()
