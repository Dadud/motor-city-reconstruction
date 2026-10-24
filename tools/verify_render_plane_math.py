"""Compare the renderer's plane-height equation with original execution."""
import argparse
import random
import struct

from client.render_plane_math import plane_height
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x4b71a0)
    for index in range(cases):
        normal=(rng.uniform(-4.,4.),rng.choice((-1.,1.))*rng.uniform(.1,4.),
                rng.uniform(-4.,4.))
        reference=tuple(rng.uniform(-100.,100.) for _ in range(3))
        point=tuple(rng.uniform(-100.,100.) for _ in range(3))
        expected=plane_height(normal,reference,point)
        actual=oracle.render_plane_height(normal,reference,point)
        if _word(actual)!=_word(expected):
            raise AssertionError(f'plane-height case {index}: expected {expected!r} ({_word(expected):#x}), got {actual!r} ({_word(actual):#x})')
    return {'native-matching-plane-height-cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(verify(args.executable,args.cases))


if __name__=='__main__':
    main()
