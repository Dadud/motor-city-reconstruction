"""Compare one-plane near-W triangle clipping with direct MCO execution."""
import argparse
import random
import struct

from client.render_polygon_clip import (clip_triangle_near_plane,
    clip_triangle_near_then_y_max,clip_triangle_near_then_y_min,
    clip_triangle_near_then_x_plane,
    clip_triangle_near_then_y_max_then_x_min)
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(executable,cases=256):
    if type(cases) is not int or not 1<=cases<=10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de001)
    for index in range(cases):
        outside=index%3
        codes=tuple(1 if i==outside else 0 for i in range(3))
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
            w=(rng.uniform(0.01,0.099) if vertex==outside else
               rng.uniform(0.2,0.95))
            records.append((_word(rng.uniform(-20.,20.)),
                            _word(rng.uniform(-20.,20.)),
                            _word(rng.uniform(-1.,1.)),_word(w),
                            colors[vertex],rng.getrandbits(32),
                            _word(rng.uniform(0.,1.)),
                            _word(rng.uniform(0.,1.)),
                            rng.getrandbits(32),rng.getrandbits(32)))
        records=tuple(records)
        expected_count,expected_vertices=clip_triangle_near_plane(
            codes,records,plane_w=0.1,near_w=1.,far_w=0.)
        actual=oracle.render_polygon_near_clip(
            codes,records,plane_w=0.1,near_w=1.,far_w=0.)
        if actual is None or (actual[0],actual[3])!=(expected_count,
                                                      expected_vertices):
            raise AssertionError(
                f'case {index}: expected {(expected_count,expected_vertices)!r}, '
                f'got {actual!r}; codes={codes!r}; records={records!r}')
    return {'native-matching-near-plane-polygons':cases}


def verify_composed(executable,cases=128):
    """Check native calls with near-W and upper-Y passes both enabled."""
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de009)
    for index in range(cases):
        outside=index%3
        y_max=rng.uniform(-2.,2.)
        y_min=-y_max
        colors=[rng.getrandbits(32) for _ in range(3)]
        records=[]; codes=[]
        for vertex in range(3):
            w=(rng.uniform(.01,.09) if vertex==outside else
               rng.uniform(.2,.95))
            y=(y_max+rng.uniform(.1,3.) if vertex==outside else
               y_max-rng.uniform(.1,3.))
            records.append((_word(rng.uniform(-20,20)),_word(y),
                _word(rng.uniform(-1,1)),_word(w),colors[vertex],
                rng.getrandbits(32),_word(rng.random()),_word(rng.random()),
                rng.getrandbits(32),rng.getrandbits(32)))
            codes.append((1 if w<.1 else 0)|(8 if y>y_max else 0))
        records=tuple(records); codes=tuple(codes)
        expected=clip_triangle_near_then_y_max(codes,records,
            plane_w=.1,y_max=y_max,near_w=1.,far_w=0.)
        actual=oracle.render_polygon_multi_clip(codes,records,
            plane_mask=0x09,plane_w=.1,y_max=y_max,near_w=1.,far_w=0.)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(f'composed case {index}: expected {expected!r}, got {actual!r}; codes={codes!r}')
    return {'native-matching-near-plus-upper-Y-polygons':cases}


def verify_composed_lower(executable,cases=128):
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de004)
    for index in range(cases):
        outside=index%3
        y_min=rng.uniform(-2.,2.)
        colors=[rng.getrandbits(32) for _ in range(3)]
        records=[]; codes=[]
        for vertex in range(3):
            w=(rng.uniform(.01,.09) if vertex==outside else
               rng.uniform(.2,.95))
            y=(y_min-rng.uniform(.1,3.) if vertex==outside else
               y_min+rng.uniform(.1,3.))
            records.append((_word(rng.uniform(-20,20)),_word(y),
                _word(rng.uniform(-1,1)),_word(w),colors[vertex],
                rng.getrandbits(32),_word(rng.random()),_word(rng.random()),
                rng.getrandbits(32),rng.getrandbits(32)))
            codes.append((1 if w<.1 else 0)|(4 if y<y_min else 0))
        records=tuple(records); codes=tuple(codes)
        expected=clip_triangle_near_then_y_min(codes,records,
            plane_w=.1,y_min=y_min,near_w=1.,far_w=0.)
        actual=oracle.render_polygon_multi_clip(codes,records,
            plane_mask=0x05,plane_w=.1,y_min=y_min,near_w=1.,far_w=0.)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(f'composed lower-Y case {index}: expected {expected!r}, got {actual!r}; codes={codes!r}')
    return {'native-matching-near-plus-lower-Y-polygons':cases}


def verify_composed_x(executable,cases=128,*,upper=False):
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de020 if upper else 0x475de010)
    bit=0x20 if upper else 0x10
    results=0
    for index in range(cases):
        outside=index%3
        boundary=rng.uniform(-2.,2.)
        colors=[rng.getrandbits(32) for _ in range(3)]
        records=[]; codes=[]
        for vertex in range(3):
            w=(rng.uniform(.01,.09) if vertex==outside else
               rng.uniform(.2,.95))
            x=(boundary+rng.uniform(.1,3.) if vertex==outside else
               boundary-rng.uniform(.1,3.)) if upper else (
               boundary-rng.uniform(.1,3.) if vertex==outside else
               boundary+rng.uniform(.1,3.))
            records.append((_word(x),_word(rng.uniform(-10,10)),
                _word(rng.uniform(-1,1)),_word(w),colors[vertex],
                rng.getrandbits(32),_word(rng.random()),_word(rng.random()),
                rng.getrandbits(32),rng.getrandbits(32)))
            codes.append((1 if w<.1 else 0)|(bit if ((x>boundary) if upper else (x<boundary)) else 0))
        records=tuple(records); codes=tuple(codes)
        expected=clip_triangle_near_then_x_plane(codes,records,
            plane_w=.1,x_boundary=boundary,upper=upper,near_w=1.,far_w=0.)
        kwargs={'x_max':boundary} if upper else {'x_min':boundary}
        actual=oracle.render_polygon_multi_clip(codes,records,
            plane_mask=0x21 if upper else 0x11,plane_w=.1,
            near_w=1.,far_w=0.,**kwargs)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(f'composed X case {index}, upper={upper}: expected {expected!r}, got {actual!r}; codes={codes!r}')
        results+=1
    return {'native-matching-near-plus-right-X-polygons' if upper else
            'native-matching-near-plus-left-X-polygons':results}


def verify_composed_three_planes(executable,cases=128):
    oracle=DynoOracle(executable)
    rng=random.Random(0x475de018)
    for index in range(cases):
        outside=index%3
        y_max=rng.uniform(-2.,2.); x_min=rng.uniform(-2.,2.)
        records=[]; codes=[]; colors=[rng.getrandbits(32) for _ in range(3)]
        for vertex in range(3):
            w=(rng.uniform(.01,.09) if vertex==outside else rng.uniform(.2,.95))
            y=(y_max+rng.uniform(.1,3.) if vertex==outside else y_max-rng.uniform(.1,3.))
            x=(x_min-rng.uniform(.1,3.) if vertex==outside else x_min+rng.uniform(.1,3.))
            records.append((_word(x),_word(y),_word(rng.uniform(-1,1)),_word(w),
                colors[vertex],rng.getrandbits(32),_word(rng.random()),
                _word(rng.random()),rng.getrandbits(32),rng.getrandbits(32)))
            codes.append((1 if w<.1 else 0)|(8 if y>y_max else 0)|
                         (0x10 if x<x_min else 0))
        records=tuple(records);codes=tuple(codes)
        expected=clip_triangle_near_then_y_max_then_x_min(codes,records,
            plane_w=.1,y_max=y_max,x_min=x_min,near_w=1.,far_w=0.)
        actual=oracle.render_polygon_multi_clip(codes,records,
            plane_mask=0x19,plane_w=.1,y_max=y_max,x_min=x_min,
            near_w=1.,far_w=0.)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(f'three-plane case {index}: expected {expected!r}, got {actual!r}; codes={codes!r}')
    return {'native-matching-near-upper-Y-left-X-polygons':cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x475de0 near-plane crossing matches {verify(args.executable,args.cases)}')
    print(f'0x475de0 composed clipping matches {verify_composed(args.executable)}')
    print(f'0x475de0 lower-Y composition matches {verify_composed_lower(args.executable)}')
    print(f'0x475de0 left-X composition matches {verify_composed_x(args.executable,upper=False)}')
    print(f'0x475de0 right-X composition matches {verify_composed_x(args.executable,upper=True)}')
    print(f'0x475de0 three-plane composition matches {verify_composed_three_planes(args.executable)}')


if __name__=='__main__':
    main()
