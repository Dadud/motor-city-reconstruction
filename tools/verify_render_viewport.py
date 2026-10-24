"""Compare recovered viewport setup with direct mcity.exe execution."""
import argparse
import random
import struct

from client.render_viewport import (RenderViewport, classify_render_position,
                                    configure_render_viewport)
from tools.native_oracle import DynoOracle


def _words(values):
    return tuple(struct.unpack('<I',struct.pack('<f',value))[0]
                 for value in values)


def verify(executable,cases=512):
    if type(cases) is not int or not 1 <= cases <= 20_000:
        raise ValueError('cases must be between 1 and 20000')
    rng=random.Random(0x6cb610)
    oracle=DynoOracle(executable)
    for index in range(cases):
        plane_z0=rng.uniform(.05,.5)
        plane_z1=plane_z0+rng.uniform(1.,1000.)
        viewport=(rng.uniform(-200.,200.),rng.uniform(-150.,150.),
                  rng.uniform(1.,1920.),rng.uniform(1.,1080.),
                  plane_z0,plane_z1)
        records=[bytearray(bytes([0xcd])*32) for _ in range(100)]
        state=configure_render_viewport(RenderViewport(*viewport),records)
        native_words,native_records=oracle.render_viewport_state(viewport)
        expected_words=_words(tuple(state.globals_by_address().values()))
        if expected_words!=native_words:
            raise AssertionError(
                f'case {index}: expected globals={expected_words!r}, '
                f'actual={native_words!r}, viewport={viewport!r}')
        expected=bytearray(bytes([0xcd])*3200)
        for slot in range(100):
            struct.pack_into('<I',expected,slot*32+0x14,0)
        if bytes(expected)!=native_records:
            raise AssertionError(f'case {index}: scratch-table writes differ')
        points=((state.x_min,state.y_min,.5,state.w_plane_z0),
                (state.x_max,state.y_max,1.,state.w_plane_z0),
                (state.x_min-1.,state.y_min,.25,state.w_plane_z0),
                (state.x_min,state.y_min-1.,.75,state.w_plane_z0))
        bounds=state.clip_code_bounds()
        raw_bounds=(bounds.x_lower,bounds.x_upper,bounds.y_lower,
                    bounds.y_upper,bounds.w_upper,bounds.z_lower)
        for point in points:
            expected_code=classify_render_position(point,state)
            raw_point=struct.unpack('<4i',struct.pack('<4f',*point))
            actual_code=oracle.render_clip_code(raw_point,raw_bounds)
            if expected_code!=actual_code:
                raise AssertionError(
                    f'case {index}: viewport-derived clip code differs '
                    f'for point {point!r}')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x6cb610 matches {verify(args.executable,args.cases)} viewport cases')


if __name__=='__main__':
    main()
