"""Compare the recovered segment clipper with direct original execution."""
import argparse
import random
import struct

from client.render_segment_clip import SegmentClipBounds, clip_render_segment
from tools.native_oracle import DynoOracle


def _bits(segment):
    if segment is None:
        return None
    return tuple(struct.pack('<6f',*point) for point in segment)


def _code(point,bounds):
    x,y,_,w=point[:4]
    result=0
    if w < bounds.near_w:
        result|=0x01
    elif w > bounds.far_w:
        result|=0x02
    if x < bounds.x_min:
        result|=0x10
    elif x > bounds.x_max:
        result|=0x20
    if y < bounds.y_min:
        result|=0x04
    elif y > bounds.y_max:
        result|=0x08
    return result


def verify(executable,cases=512):
    if type(cases) is not int or not 1 <= cases <= 20_000:
        raise ValueError('cases must be between 1 and 20000')
    bounds=SegmentClipBounds(.1,1.,-1.,1.,-1.,1.,0xcf)
    native_bounds=(bounds.near_w,bounds.far_w,bounds.x_min,bounds.x_max,
                   bounds.y_min,bounds.y_max,bounds.xy_mask)
    oracle=DynoOracle(executable)
    rng=random.Random(0x6cb970)
    pairs=[]
    for _ in range(cases):
        points=[]
        for _ in range(2):
            points.append((rng.uniform(-3.,3.),rng.uniform(-3.,3.),
                           rng.uniform(-2.,2.),rng.uniform(-.2,1.5),
                           rng.uniform(-1.,1.),rng.uniform(-1.,1.)))
        pairs.append((tuple(points[0]),tuple(points[1])))
    compared=0
    for index,(first,second) in enumerate(pairs):
        first_code,second_code=_code(first,bounds),_code(second,bounds)
        expected=clip_render_segment(first,second,first_code,second_code,bounds)
        actual=oracle.render_segment_clip(first,second,first_code,second_code,
                                          native_bounds)
        if _bits(expected)!=_bits(actual):
            raise AssertionError(
                f'case {index}: codes=({first_code:#04x},{second_code:#04x}), '
                f'expected={expected!r}, actual={actual!r}')
        compared+=1
    return compared


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x6cb970 matches {verify(args.executable,args.cases)} segment cases')


if __name__=='__main__':
    main()
