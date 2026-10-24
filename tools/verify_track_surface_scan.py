"""Compare the four-point-stride track selector with original MCO."""
import argparse
import random
import struct

from client.track_surface_query import nearest_track_quarter_point
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x42d4b0)
    for case in range(cases):
        count=1+case%64
        rows=[]
        for _ in range(count):
            row=bytearray(rng.getrandbits(8) for _ in range(0x54))
            struct.pack_into('<3f',row,0,rng.uniform(-1500.,1500.),
                             rng.uniform(-50.,50.),rng.uniform(-1500.,1500.))
            rows.append(bytes(row))
        point=tuple(rng.uniform(-1600.,1600.) for _ in range(3))
        expected=nearest_track_quarter_point(point,rows)
        actual=oracle.nearest_track_quarter_point(point,rows)
        if actual!=expected:
            raise AssertionError(f'quarter scan case {case}: expected {expected}, got {actual}; rows={count}')
    return {'native-matching-four-point-track-scan-cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(verify(args.executable,args.cases))


if __name__=='__main__':
    main()
