"""Compare the +/-4 track-point selector with the original executable."""
import argparse
import random
import struct

from client.track_surface_query import nearest_track_neighbor
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x42d3e0)
    for case in range(cases):
        count=9+case%32
        rows=[]
        for _ in range(count):
            row=bytearray(rng.getrandbits(8) for _ in range(0x54))
            struct.pack_into('<3f',row,0,rng.uniform(-1000.,1000.),
                             rng.uniform(-50.,50.),rng.uniform(-1000.,1000.))
            rows.append(bytes(row))
        index=rng.randrange(count)
        point=tuple(rng.uniform(-1200.,1200.) for _ in range(3))
        expected=nearest_track_neighbor(point,rows,index)
        actual=oracle.nearest_track_neighbor(point,rows,index)
        if actual!=expected:
            raise AssertionError(f'neighbor case {case}: expected {expected}, got {actual}; count={count}, index={index}')
    return {'native-matching-wrapped-track-neighbor-cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(verify(args.executable,args.cases))


if __name__=='__main__':
    main()
