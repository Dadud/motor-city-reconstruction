"""Compare the cached quad-hit branch of 0x42e760 with MCO execution."""
import argparse
import random
import struct

from client.track_surface_query import cached_quad_hit
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x42e760)
    for index in range(cases):
        x0=rng.uniform(-1000.,0.); x1=x0+rng.uniform(.1,1000.)
        z0=rng.uniform(-1000.,0.); z1=z0+rng.uniform(.1,1000.)
        quad=((x0,rng.uniform(-20.,20.),z0),
              (x1,rng.uniform(-20.,20.),z0),
              (x1,rng.uniform(-20.,20.),z1),
              (x0,rng.uniform(-20.,20.),z1))
        point=(rng.uniform(x0,x1),rng.uniform(-100.,100.),
               rng.uniform(z0,z1))
        expected=cached_quad_hit(point,quad)
        result,before,after=oracle.track_surface_cached_quad(point,quad)
        context=bytearray(before)
        if expected is not None:
            struct.pack_into('<3f',context,8*4,*expected)
        if result!=1 or after!=bytes(context):
            raise AssertionError(f'cached quad case {index}: expected 1/{bytes(context).hex()}, got {result}/{after.hex()}')
    return {'native-matching-cached-quad-hit-cases':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(verify(args.executable,args.cases))


if __name__=='__main__':
    main()
