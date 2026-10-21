"""Compare native and Python translations of the 0x458530 impact response."""
import argparse
import json
import struct
import subprocess
from dataclasses import replace

from client.collision_pair_response import resolve_pair_impulse
from tools.collision_pair_response_oracle import cases


def body_values(body):
    inertia = body.inertia
    return (body.address, *body.position, *body.linear_velocity,
            *body.angular_turn_velocity, *body.center_of_mass_local,
            inertia.inverse_mass, *inertia.inverse_inertia,
            *inertia.world_to_body, *inertia.body_to_world, body.mass,
            body.mode, body.response_coefficient, body.gate, body.peer_gate)


def verify(runner, case_count=256):
    corpus = list(cases(case_count))
    prepared = [(replace(owner, contact_record=bytes(0x400)),
                 replace(target, contact_record=bytes(0x400)), point, normal, coeffs)
                for owner, target, point, normal, coeffs in corpus]
    payload = ''.join(' '.join(format(value, '.17g') for value in
                               (*body_values(owner), *body_values(target),
                                *point, *normal, *coeffs)) + '\n'
                      for owner, target, point, normal, coeffs in prepared)
    process = subprocess.run([str(runner)], input=payload, capture_output=True,
                             text=True, check=True, timeout=60)
    rows = process.stdout.splitlines()
    if len(rows) != len(prepared):
        raise AssertionError('native pair-response output count differs')
    maximum = 0.0
    for index, (line, args) in enumerate(zip(rows, prepared)):
        fields = line.split()
        if len(fields) != 46:
            raise AssertionError(f'case {index} returned malformed output ({len(fields)} fields)')
        actual = [float(value) for value in fields]
        owner, target, point, normal, coeffs = args
        expected = resolve_pair_impulse(owner, target, point, normal, *coeffs)
        discrete = (int(expected.collided), expected.samples, expected.impact_status)
        if tuple(map(int, actual[:3])) != discrete:
            raise AssertionError(f'case {index} hit/sample/status differs')
        wanted = (expected.effective_mass, *expected.owner.linear_velocity,
                  *expected.owner.angular_turn_velocity, *expected.target.linear_velocity,
                  *expected.target.angular_turn_velocity)
        for component, (a, b) in enumerate(zip(actual[3:16], wanted)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(3e-5, abs(b) * 5e-6):
                raise AssertionError(f'case {index} velocity[{component}] differs: {a} != {b}')
        for body_index, expected_body in enumerate((expected.owner, expected.target)):
            values = actual[16 + body_index * 15:31 + body_index * 15]
            record = expected_body.contact_record
            pointer = int.from_bytes(record[0x3c4:0x3c8], 'little')
            status = int.from_bytes(record[0x3e4:0x3e8], 'little')
            counts = (int.from_bytes(record[0x3f4:0x3f8], 'little'),
                      int.from_bytes(record[0x3f8:0x3fc], 'little'))
            ints = (pointer, status, *counts)
            if tuple(map(int, (values[0], values[8], values[12], values[13]))) != ints:
                raise AssertionError(f'case {index} record {body_index} integer fields differ')
            offsets = (0x3c8, 0x3cc, 0x3d0, 0x3d4, 0x3d8, 0x3dc, 0x3e0,
                       0x3e8, 0x3ec, 0x3f0, 0x3fc)
            positions = (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 14)
            for pos, offset in zip(positions, offsets):
                wanted_float = struct.unpack_from('<f', record, offset)[0]
                error = abs(values[pos] - wanted_float)
                maximum = max(maximum, error)
                if error > max(3e-5, abs(wanted_float) * 5e-6):
                    raise AssertionError(f'case {index} record {body_index} float[{pos}] differs')
    return {'cases': len(prepared), 'maximum_absolute_error': maximum,
            'scope': 'native/Python sampled pair impact response 0x458530'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(verify(args.runner, args.cases)))


if __name__ == '__main__':
    main()
