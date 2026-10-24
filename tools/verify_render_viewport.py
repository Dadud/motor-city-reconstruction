"""Compare recovered viewport setup with direct mcity.exe execution."""
import argparse
import random
import struct

from client.render_viewport import (RenderViewport, classify_render_position,
                                    configure_render_viewport,
                                    prepare_render_viewport_request,
                                    RenderViewportRequest,
                                    set_alternate_render_bounds)
from tools.native_oracle import DynoOracle


def _words(values):
    return tuple(struct.unpack('<I',struct.pack('<f',value))[0]
                 for value in values)


_REQUEST_GLOBALS=(
    0xaa43c0,0xaa43c4,0xaa43c8,0xaa43cc,
    0x8c672c,0xb31fbc,0xb31fc0,0x8c6730,0xb424c8,0xb424bc,
    0xb424c4,0xb424b8,0xb31fc4,0xb424c0,0xb424b0,0xb424a4,
    0xb31fc8,0xb424a0,0xb424a8,0xb424ac,0xb424b4,
    0x993848,0x9938b0,0x9938ac,0x993bb0,0x993a4c,0x9938a8,
    0x99248c,0x993840,0x993a48,0x993bb4,0x993844,0x992488)


def _word(value):
    if type(value) is int:
        return value & 0xffffffff
    return struct.unpack('<I',struct.pack('<f',value))[0]


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
        alternate=tuple(rng.uniform(-500.,2500.) for _ in range(4))
        expected_alternate=_words(tuple(
            set_alternate_render_bounds(*alternate).globals_by_address().values()))
        actual_alternate=oracle.alternate_render_bounds(alternate)
        if expected_alternate!=actual_alternate:
            raise AssertionError(
                f'case {index}: 0x474d00 globals differ: '
                f'{expected_alternate!r} != {actual_alternate!r}')
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
        surface_width=rng.randint(1,2048)
        surface_height=rng.randint(1,1152)
        rect=(rng.randint(-200,2200),rng.randint(-150,1300),
              rng.randint(-100,2400),rng.randint(-100,1400))
        alternate=bool(index&1)
        request=RenderViewportRequest(surface_width,surface_height,*rect,
                                      alternate_path=alternate)
        result=prepare_render_viewport_request(request)
        expected_request=tuple(_word(result.globals_by_address.get(address,0xcccccccc))
                               for address in _REQUEST_GLOBALS)
        actual_request,request_records,callback_count=oracle.render_viewport_request(
            surface_width,surface_height,rect,alternate_path=alternate)
        if expected_request!=actual_request:
            raise AssertionError(
                f'case {index}: 0x5668c0 globals differ: '
                f'{expected_request!r} != {actual_request!r}; request={request!r}')
        if callback_count != int(not alternate):
            raise AssertionError(f'case {index}: viewport callback count differs')
        expected_records=bytearray(bytes([0xcd])*3200)
        if not alternate:
            for slot in range(100):
                struct.pack_into('<I',expected_records,slot*32+0x14,0)
        if bytes(expected_records)!=request_records:
            raise AssertionError(f'case {index}: 0x5668c0 scratch writes differ')
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases',type=int,default=512)
    args=parser.parse_args()
    print(f'0x5668c0 viewport flow matches {verify(args.executable,args.cases)} cases')


if __name__=='__main__':
    main()

