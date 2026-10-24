"""Compare the all-inside four-vertex dispatcher branch with MCO."""
import argparse
import random
import struct

from client.render_quad_dispatch import (
    dispatch_first_fan_triangle, dispatch_inside_quad)
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(executable,cases=256):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x474ee0)
    counts={'quad-callback':0,'triangle-callback':0,'triangle-rejected':0}
    for index in range(cases):
        near=10.0
        far=-100.0
        vertices=[]
        for _ in range(4):
            w=(rng.uniform(0.,near+4.) if rng.randrange(3) else
               -rng.uniform(0.,4.))
            vertices.append((
                _word(rng.uniform(-1000.,1000.)),
                _word(rng.uniform(-1000.,1000.)),
                rng.getrandbits(32),_word(w),rng.getrandbits(32),
                rng.getrandbits(24)<<8,rng.getrandbits(32),
                rng.getrandbits(32)))
        if index%7==0:
            vertices[2]=tuple(vertices[2][:7]+(0xffc00000,))
        vertices=tuple(vertices)
        expected=dispatch_inside_quad(vertices,near,far).callback_words
        actual=oracle.render_quad_inside(vertices,near,far)
        if expected!=actual:
            raise AssertionError(f'case {index}: expected {expected!r}, got {actual!r}')
        counts['quad-callback']+=1

        triangle=list(vertices)
        triangle[3]=tuple(triangle[3][:5]+(0x10,)+triangle[3][6:])
        if index%7==0:
            changed=list(triangle[1]); changed[7]=0xffc00000
            triangle[1]=tuple(changed)
        triangle=tuple(triangle)
        expected_triangle=dispatch_first_fan_triangle(triangle,near,far).callback_words
        actual_triangle=oracle.render_quad_first_triangle(triangle,near,far)
        if expected_triangle!=actual_triangle:
            raise AssertionError(
                f'triangle case {index}: expected {expected_triangle!r}, '
                f'got {actual_triangle!r}')
        counts['triangle-callback' if expected_triangle is not None else
               'triangle-rejected']+=1
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x474ee0 verified branches match {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
