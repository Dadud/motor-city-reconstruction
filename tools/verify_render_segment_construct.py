"""Compare 0x482610 endpoint construction and clipping with MCO execution."""
import argparse
import random
import struct

from client.render_clip_code import RenderClipBounds
from client.render_segment_clip import SegmentClipBounds
from client.render_segment_construct import construct_render_segment
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<i',struct.pack('<f',value))[0]


def verify(executable,cases=512):
    if type(cases) is not int or not 1 <= cases <= 20_000:
        raise ValueError('cases must be between 1 and 20000')
    clip_codes=RenderClipBounds(_word(-100.),_word(100.),
                                _word(-100.),_word(100.),
                                _word(1.),_word(1.))
    segment_bounds=SegmentClipBounds(10.,0.0016666667,
                                     -100.,100.,-100.,100.,0xcf)
    rng=random.Random(0x482610)
    oracle=DynoOracle(executable)
    counts={'pass-through':0,'clipped':0,'rejected':0}
    for index in range(cases):
        mode=index%4
        if mode==0:
            coordinates=tuple(rng.randint(-80,80) for _ in range(4))
        elif mode==1:
            coordinates=(rng.randint(120,200),rng.randint(-80,80),
                         rng.randint(-80,80),rng.randint(-80,80))
        elif mode==2:
            coordinates=(rng.randint(120,200),rng.randint(-80,80),
                         rng.randint(120,200),rng.randint(-80,80))
        else:
            coordinates=tuple(rng.randint(-200,200) for _ in range(4))
        attributes=(rng.getrandbits(32),rng.getrandbits(32))
        opaque=(rng.getrandbits(32),rng.getrandbits(32))
        expected=construct_render_segment(
            *coordinates,*attributes,clip_codes,segment_bounds,
            opaque_words=opaque)
        actual=oracle.render_segment_construct(
            coordinates,attributes,opaque,clip_codes,segment_bounds)
        if expected.clipped_words!=actual:
            raise AssertionError(
                f'case {index}: expected {expected.clipped_words!r}, '
                f'got {actual!r}; coordinates={coordinates!r}; '
                f'codes=({expected.first_code:#x},{expected.second_code:#x})')
        if expected.clipped_words is None:
            counts['rejected']+=1
        elif expected.first_code==0 and expected.second_code==0:
            counts['pass-through']+=1
        else:
            counts['clipped']+=1
    if not all(counts.values()):
        raise AssertionError(f'corpus missed a path: {counts!r}')
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x482610 matches {verify(args.executable,args.cases)}')


if __name__=='__main__':
    main()
