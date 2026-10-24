"""Compare ordered multi-plane 0x475de0 clipping against MCO execution."""
import argparse
import random
import struct

from client.render_polygon_clip import clip_triangle_planes
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def _code(x,y,w,*,plane_w,y_min,y_max,x_min,x_max):
    return ((1 if w>plane_w else 0) |
            (4 if y<y_min else 0) | (8 if y>y_max else 0) |
            (0x10 if x<x_min else 0) | (0x20 if x>x_max else 0))


def verify(executable,cases=512):
    if type(cases) is not int or not 1<=cases<=20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x475de018)
    oracle=DynoOracle(executable)
    # Include every nonempty subset of the five clipping planes, with
    # simultaneous outcodes and generated intersections feeding later passes.
    masks=tuple(mask for mask in range(1,0x40) if not mask&~0x3d)
    for index in range(cases):
        plane_mask=masks[index%len(masks)]
        plane_w=0.1; near_w=1.; far_w=0.
        x_min=rng.uniform(-5.,-0.5); x_max=rng.uniform(.5,5.)
        y_min=rng.uniform(-5.,-0.5); y_max=rng.uniform(.5,5.)
        records=[]; codes=[]
        for vertex in range(3):
            def coordinate(lo,hi,low_bit,high_bit):
                outside=rng.randrange(4)
                if outside==1 and plane_mask&low_bit:
                    return rng.uniform(lo-4.,lo-.01)
                if outside==2 and plane_mask&high_bit:
                    return rng.uniform(hi+.01,hi+4.)
                return rng.uniform(lo+.01,hi-.01)
            x=coordinate(x_min,x_max,0x10,0x20)
            y=coordinate(y_min,y_max,0x04,0x08)
            if plane_mask&1 and rng.randrange(4)==1:
                w=rng.uniform(plane_w+.01,plane_w+.6)
            else:
                w=rng.uniform(.01,plane_w-.001)
            color=rng.getrandbits(32)
            records.append((_word(x),_word(y),_word(rng.uniform(-1.,1.)),
                _word(w),color,rng.getrandbits(32),_word(rng.random()),
                _word(rng.random()),rng.getrandbits(32),rng.getrandbits(32)))
            codes.append(_code(x,y,w,plane_w=plane_w,y_min=y_min,
                               y_max=y_max,x_min=x_min,x_max=x_max))
        records=tuple(records); codes=tuple(codes)
        plane_mask &= (codes[0]|codes[1]|codes[2])
        if plane_mask==0:
            # Regenerate the near-plane crossing when a sampled mask has no
            # matching active outcode; the all-inside path is covered by the
            # quad-dispatch corpus.
            plane_mask=1
            codes=tuple((code&~1) | (1 if i==0 else 0)
                        for i,code in enumerate(codes))
            changed=list(records[0]); changed[3]=_word(plane_w+.2)
            records=(tuple(changed),records[1],records[2])
        expected=clip_triangle_planes(codes,records,plane_mask=plane_mask,
            plane_w=plane_w,y_min=y_min,y_max=y_max,x_min=x_min,x_max=x_max,
            near_w=near_w,far_w=far_w)
        actual=oracle.render_polygon_multi_clip(codes,records,
            plane_mask=plane_mask,plane_w=plane_w,y_min=y_min,y_max=y_max,
            x_min=x_min,x_max=x_max,near_w=near_w,far_w=far_w)
        if expected==(0xffffffff,()):
            matches=actual is None
        else:
            matches=actual is not None and (actual[0],actual[3])==expected
        if not matches:
            raise AssertionError(
                f'case {index}: mask={plane_mask:#x}; codes={codes!r}; '
                f'expected={expected!r}; actual={actual!r}; '
                f'records={records!r}; bounds={(x_min,x_max,y_min,y_max)!r}')
    depth_cases=min(cases,64)
    for index in range(depth_cases):
        records=tuple((
            _word(x),_word(y),_word(.25),_word(.5),rng.getrandbits(32),
            rng.getrandbits(32),_word(rng.random()),_word(rng.random()),
            rng.getrandbits(32),rng.getrandbits(32))
            for x,y in ((-.5,-.5),(.5,-.5),(0.,.5)))
        codes=(2,2,2)
        kwargs=dict(plane_w=.1,y_min=-1.,y_max=1.,x_min=-1.,x_max=1.,
                    near_w=1.,far_w=0.)
        expected=clip_triangle_planes(codes,records,plane_mask=0x02,**kwargs)
        actual=oracle.render_polygon_multi_clip(
            codes,records,plane_mask=0x02,**kwargs)
        if actual is None or (actual[0],actual[3])!=expected:
            raise AssertionError(
                f'depth pass-through case {index}: '
                f'expected={expected!r}; actual={actual!r}')
    return {'five-plane-cases':cases,'depth-pass-through-cases':depth_cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x475de0 ordered multi-plane cases match '
          f'{verify(args.executable,args.cases)} calls')


if __name__=='__main__':
    main()
