"""Compare native and Python 0x459150 support correction compositions."""
import argparse
import json
import struct
import subprocess

from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody
from client.collision_support import correct_support_geometry, resolve_support_contacts
from tools.support_correction_oracle import IDENTITY, _make_world, cases


def compare(runner, count=256):
    corpus = list(cases(count))
    payload = []
    expected = []
    for index, position, velocity_y, local, arena, root, seed in corpus:
        previous, neighbors = index % 3, index % 2
        world = _make_world(arena, root)
        body = CollisionImpactBody(0x71008000, position, (0., velocity_y, 0.),
                                   (0., 0., 0.), (0., 0., 0.),
                                   CollisionInertia(1., (1., 1., 1.), IDENTITY, IDENTITY),
                                   1., contact_record=bytes(0x400))
        geometry = correct_support_geometry(world, position, IDENTITY, local,
                                            (seed,) * 22, velocity_y)
        result = resolve_support_contacts(world, body, geometry,
                                          ((.45, .2),) * 32, 1., 0)
        expected.append((geometry, result))
        payload.append(' '.join(format(v, '.17g') for v in
                       (*position, velocity_y, previous, neighbors, *local,
                        *seed)) + '\n')
    process = subprocess.run([str(runner)], input=''.join(payload), capture_output=True,
                             text=True, check=True, timeout=60)
    rows = process.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native support-comparison output count differs')
    maximum = 0.
    for index, (line, (geometry, result)) in enumerate(zip(rows, expected)):
        values = line.split()
        if len(values) != 136:
            raise AssertionError(f'case {index} malformed native output ({len(values)} fields)')
        actual = [float(value) for value in values]
        if int(actual[0]) != result.support_count:
            raise AssertionError(f'case {index} support count differs')
        wanted_vectors = (*result.body.position, *result.body.linear_velocity,
                          *result.body.angular_turn_velocity,
                          *(v for point in geometry.world_points for v in point))
        for component, (a, b) in enumerate(zip(actual[1:76], wanted_vectors)):
            error = abs(a-b); maximum=max(maximum,error)
            if error > max(3e-5, abs(b)*5e-6):
                raise AssertionError(f'case {index} float[{component}] {a} != {b}')

        got_bytes = bytes(map(int, actual[76:]))
        wanted = result.body.contact_record[0x3c4:0x400]
        for offset in (0, 32, 48, 52):
            if got_bytes[offset:offset+4] != wanted[offset:offset+4]:
                raise AssertionError(f'case {index} contact integer {offset:#x} differs')
        for offset in (4, 8, 12, 16, 20, 24, 28, 36, 40, 44, 56):
            a = struct.unpack_from('<f', got_bytes, offset)[0]
            b = struct.unpack_from('<f', wanted, offset)[0]
            error = abs(a-b); maximum=max(maximum,error)
            if error > max(3e-5, abs(b)*5e-6):
                raise AssertionError(f'case {index} contact float at {offset:#x} differs')
    return {'cases':len(corpus),'maximum_absolute_error':maximum,
            'scope':'native/Python support correction and impulse composition'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner'); parser.add_argument('--cases',type=int,default=256)
    args=parser.parse_args(); print(json.dumps(compare(args.runner,args.cases)))


if __name__=='__main__': main()
