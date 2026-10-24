"""Compare the renderer polygon-bounds helper with direct MCO execution."""
import argparse
import random
import struct

from client.render_geometry import (RenderPolygonData,
                                    extract_render_polygon_bounds)
from tools.native_oracle import DynoOracle


def _word(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(executable,cases=512):
    if type(cases) is not int or not 1 <= cases <= 20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x478610)
    oracle=DynoOracle(executable)
    for index in range(cases):
        records=tuple(tuple(rng.uniform(-1000.,1000.) for _ in range(8))
                      for _ in range(rng.randint(0,16)))
        max_x=rng.uniform(-1000.,1000.)
        min_x=rng.uniform(-1000.,1000.)
        null_polygon=(index%31==0)
        polygon=None if null_polygon else RenderPolygonData(records,max_x,min_x)
        output_mask=rng.randrange(16)
        expected=extract_render_polygon_bounds(polygon)
        actual=oracle.render_polygon_bounds(records,max_x,min_x,
                                             output_mask=output_mask,
                                             null_polygon=null_polygon)
        expected_words=tuple(_word(value) if output_mask&(1<<i) else None
                             for i,value in enumerate(expected))
        if expected_words!=actual:
            raise AssertionError(
                f'case {index}: expected {expected_words!r}, got {actual!r}; '
                f'polygon={polygon!r}, output_mask={output_mask:#x}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x478610 matches {verify(args.executable,args.cases)} cases')


if __name__=='__main__':
    main()
