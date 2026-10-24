"""Compare the environment activity transition with the original binary."""
import argparse
import random
import struct

from client.render_environment import (release_environment_objects,
    set_environment_activity,build_environment_mesh_no_projection)
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle=DynoOracle(executable)
    cases=((0,0),(0x71001000,0),(0,0x71002000),
           (0x71003000,0x71004000))
    for primary,secondary in cases:
        expected=tuple((int(bool(pointer)),0)[index]
                       if pointer else None
                       for index,pointer in enumerate((primary,secondary)))
        writes=set_environment_activity(primary,secondary)
        actual=oracle.render_environment_activity(primary,secondary)
        modeled=tuple(None if write is None else write[1] for write in writes)
        if actual!=expected or modeled!=expected:
            raise AssertionError(f'{(primary,secondary)!r}: expected {expected!r}, got native={actual!r}, model={modeled!r}')
    cleanup_cases=tuple(tuple((0x71001000+index*0x100) if mask&(1<<index) else 0
                              for index in range(4)) for mask in range(16))
    for objects in cleanup_cases:
        expected=release_environment_objects(objects)
        actual=oracle.release_environment_objects(objects)
        if actual!=expected:
            raise AssertionError(f'cleanup {objects!r}: expected {expected!r}, got {actual!r}')
    rng=random.Random(0x478b20)
    mesh_cases=512
    for index in range(mesh_cases):
        row=bytearray(0x54)
        for offset in (0,4,8,0x18,0x1c,0x20,0x24,0x28,0x2c,
                       0x38,0x3c):
            struct.pack_into('<f',row,offset,rng.uniform(-5.,5.))
        struct.pack_into('<ii',row,0x44,rng.randint(-20,20),
                         rng.randint(-20,20))
        initial=bytes(rng.getrandbits(8) for _ in range(0x3d0))
        params=dict(vertical_step=rng.uniform(-2.,2.),
                    segment_step=rng.uniform(.01,.2),
                    span_scale=rng.uniform(.1,2.))
        track_index=index%3
        track_id=rng.randint(-100,100)
        reverse=bool(index&1)
        expected=build_environment_mesh_no_projection(
            row,track_index,track_id,reverse,initial,**params)
        actual=oracle.build_environment_mesh_no_projection(
            row,track_index,track_id,reverse,initial,**params)
        if actual!=expected:
            mismatch=next(offset for offset,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError(f'mesh case {index}, first differing byte {mismatch:#x}: native={actual[mismatch:mismatch+16].hex()}, model={expected[mismatch:mismatch+16].hex()}')
    return {'native-matching-environment-activity-configurations':len(cases),
            'native-matching-environment-cleanup-configurations':len(cleanup_cases),
            'native-matching-environment-mesh-no-projection-cases':mesh_cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args=parser.parse_args()
    print(verify(args.executable))


if __name__=='__main__':
    main()
