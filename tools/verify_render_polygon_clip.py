"""Compare shared near-plane polygon rejection with MCO execution."""
import argparse
import random

from client.render_polygon_clip import reject_triangle_on_shared_near_plane
from tools.native_oracle import DynoOracle


def verify(executable,cases=256):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de0)
    for index in range(cases):
        # All three vertices share the active 0x01 near-plane outcode.
        codes=tuple(1|(rng.getrandbits(7)<<1) for _ in range(3))
        records=[]
        for _ in range(3):
            records.append((rng.getrandbits(32),rng.getrandbits(32),
                            rng.getrandbits(32),0x3f800000,
                            rng.getrandbits(32),rng.getrandbits(32),
                            0x3f800000,0x3f800000,
                            rng.getrandbits(32),rng.getrandbits(32)))
        expected=reject_triangle_on_shared_near_plane(codes)
        actual=oracle.render_polygon_shared_near_reject(codes,tuple(records))
        if expected!=actual:
            raise AssertionError(
                f'case {index}: expected {expected!r}, got {actual!r}; '
                f'clip_codes={codes!r}')
    return {'shared-near-plane-rejected':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x475de0 first-plane rejection matches {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
