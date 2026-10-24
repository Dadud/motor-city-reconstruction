"""Compare rectangle texture-state reset against direct MCO execution."""
import argparse
import random

from client.render_state import select_rectangle_texture_state
from tools.native_oracle import DynoOracle


def verify(executable,cases=256):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x46abd0)
    for index in range(cases):
        cached=0 if index%2==0 else rng.getrandbits(32) or 1
        renderer_state=rng.getrandbits(32)
        expected_cache,expected_args=select_rectangle_texture_state(cached)
        actual_cache,argument,count=oracle.rectangle_texture_state(
            cached,renderer_state)
        expected_count=len(expected_args)
        expected_argument=expected_args[0] if expected_args else None
        if (actual_cache,argument,count)!=(expected_cache,expected_argument,
                                           expected_count):
            raise AssertionError(
                f'case {index}: expected {(expected_cache,expected_argument,expected_count)!r}, '
                f'got {(actual_cache,argument,count)!r}; '
                f'cached={cached:#x}, renderer_state={renderer_state:#x}')
    return {'cache-hit':cases//2,'cache-miss':cases-cases//2}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x46abd0(0) matches {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
