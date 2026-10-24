"""Compare native rectangle-member copies with the recovered implementation."""
import argparse
import random

from client.render_geometry import copy_render_rect_fields
from tools.native_oracle import DynoOracle


def verify(executable,cases=512):
    if type(cases) is not int or not 1 <= cases <= 20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x47f990)
    oracle=DynoOracle(executable)
    for index in range(cases):
        memory=bytearray(rng.randbytes(256))
        source=rng.randrange(0,256-0x14+1)
        destination=rng.randrange(0,256-0x14+1)
        expected=bytearray(memory)
        copy_render_rect_fields(expected,source,destination)
        actual=oracle.copy_render_rect_fields(memory,source,destination)
        if bytes(expected)!=actual:
            raise AssertionError(
                f'case {index}: memory differs for source={source}, '
                f'destination={destination}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x47f990 matches {verify(args.executable,args.cases)} memory cases')


if __name__=='__main__':
    main()
