"""Compare one-plane near-W triangle clipping with direct MCO execution."""
import argparse
import random
import struct

from client.render_polygon_clip import clip_triangle_near_plane
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args()
    print(f'0x475de0 near-plane crossing matches {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
