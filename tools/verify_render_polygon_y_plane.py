"""Compare isolated upper-Y polygon clipping with MCO execution."""
import argparse
import random
import struct

from client.render_polygon_clip import (
    clip_triangle_y_max_plane, clip_triangle_y_min_plane)
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(executable,cases=256):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de008)
    lower_cases=0
    for index in range(cases):
        outside=index%3
        y_max=rng.uniform(-4.,4.)
        codes=tuple(0x08 if i==outside else 0 for i in range(3))
        colors=[rng.getrandbits(32) for _ in range(3)]
        mode=index%4
        if mode==1:
            colors=[(color&0x00ffffff)|0xff000000 for color in colors]
        elif mode==2:
            shared=rng.getrandbits(24)
            colors=[(rng.randrange(256)<<24)|shared for _ in range(3)]
        elif mode==3:
            colors=[0xff123456]*3
        records=[]
        for vertex in range(3):
            y=(y_max+rng.uniform(.01,5.) if vertex==outside else
               y_max-rng.uniform(.01,5.))
            records.append((_word(rng.uniform(-20.,20.)),_word(y),
                            _word(rng.uniform(-1.,1.)),
                            _word(rng.uniform(.2,.95)),colors[vertex],
                            rng.getrandbits(32),_word(rng.random()),
                            _word(rng.random()),rng.getrandbits(32),
                            rng.getrandbits(32)))
        records=tuple(records)
        expected=clip_triangle_y_max_plane(
            codes,records,y_max=y_max,near_w=1.,far_w=0.)
        actual=oracle.render_polygon_y_max_clip(
            codes,records,y_max=y_max,near_w=1.,far_w=0.)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(
                f'upper-Y case {index}: expected {expected!r}, got {actual!r}; '
                f'y_max={y_max!r}, codes={codes!r}')

        y_min=rng.uniform(-4.,4.)
        lower_codes=tuple(0x04 if i==outside else 0 for i in range(3))
        lower_records=[]
        for vertex in range(3):
            y=(y_min-rng.uniform(.01,5.) if vertex==outside else
               y_min+rng.uniform(.01,5.))
            lower_records.append((_word(rng.uniform(-20.,20.)),_word(y),
                                  _word(rng.uniform(-1.,1.)),
                                  _word(rng.uniform(.2,.95)),colors[vertex],
                                  rng.getrandbits(32),_word(rng.random()),
                                  _word(rng.random()),rng.getrandbits(32),
                                  rng.getrandbits(32)))
        lower_records=tuple(lower_records)
        expected_lower=clip_triangle_y_min_plane(
            lower_codes,lower_records,y_min=y_min,near_w=1.,far_w=0.)
        actual_lower=oracle.render_polygon_y_min_clip(
            lower_codes,lower_records,y_min=y_min,near_w=1.,far_w=0.)
        if actual_lower is None or (actual_lower[0],actual_lower[3])!=expected_lower:
            raise AssertionError(
                f'lower-Y case {index}: expected {expected_lower!r}, '
                f'got {actual_lower!r}; y_min={y_min!r}')
        lower_cases+=1
    return {'native-matching-upper-Y-polygons':cases,
            'native-matching-lower-Y-polygons':lower_cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x475de0 Y-plane clipping matches {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
