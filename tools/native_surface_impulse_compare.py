"""Compare native and Python implementations of support impulse 0x457df0."""
import argparse
import json
import struct
import subprocess
from dataclasses import replace

from client.collision_pair_response import resolve_surface_impulse
from tools.collision_pair_response_oracle import cases


def body_values(body):
    inertia = body.inertia
    return (body.address, *body.position, *body.linear_velocity,
            *body.angular_turn_velocity, *body.center_of_mass_local,
            inertia.inverse_mass, *inertia.inverse_inertia,
            *inertia.world_to_body, *inertia.body_to_world, body.mass,
            body.mode, body.response_coefficient, body.gate, body.peer_gate,
            body.embedded_contact_pointer)


def compare(runner, count=128):
    corpus = [(replace(body, contact_record=bytes(0x400)), contact, normal, coeffs)
              for body, _target, contact, normal, coeffs in cases(count)]
    payload = ''.join(' '.join(format(v, '.17g') for v in
                               (*body_values(body), *contact, *normal, *coeffs)) + '\n'
                      for body, contact, normal, coeffs in corpus)
    process = subprocess.run([str(runner)], input=payload, capture_output=True,
                             text=True, check=True, timeout=60)
    rows = process.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native surface-impulse output count differs')
    maximum = 0.0
    for index, (line, args) in enumerate(zip(rows, corpus)):
        fields = line.split()
        if len(fields) != 24:
            raise AssertionError(f'case {index} malformed output ({len(fields)} fields)')
        actual = [float(value) for value in fields]
        body, contact, normal, coeffs = args
        expected = resolve_surface_impulse(body, contact, normal, *coeffs)
        if tuple(map(int, actual[:3])) != (int(expected.collided), expected.samples,
                                           expected.impact_status):
            raise AssertionError(f'case {index} decision/sample/status differs')
        wanted = (*expected.body.linear_velocity, *expected.body.angular_turn_velocity)
        for component, (a, b) in enumerate(zip(actual[3:9], wanted)):
            error = abs(a-b); maximum = max(maximum, error)
            if error > max(3e-5, abs(b)*5e-6):
                raise AssertionError(f'case {index} velocity[{component}] differs: {a} != {b}')
        record = expected.body.contact_record
        ints = (int.from_bytes(record[o:o+4], 'little') for o in (0x3c4,0x3e4,0x3f4,0x3f8))
        if tuple(map(int, (actual[9],actual[17],actual[21],actual[22]))) != tuple(ints):
            raise AssertionError(f'case {index} contact record integer fields differ')
        for pos, offset in zip((10,11,12,13,14,15,16,18,19,20,23),
                               (0x3c8,0x3cc,0x3d0,0x3d4,0x3d8,0x3dc,0x3e0,
                                0x3e8,0x3ec,0x3f0,0x3fc)):
            wanted_float = struct.unpack_from('<f', record, offset)[0]
            error = abs(actual[pos]-wanted_float); maximum=max(maximum,error)
            if error > max(3e-5, abs(wanted_float)*5e-6):
                raise AssertionError(f'case {index} record float at {offset:#x} differs')
    return {'cases':len(corpus),'maximum_absolute_error':maximum,
            'scope':'native/Python single-body support impulse 0x457df0'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner'); parser.add_argument('--cases',type=int,default=128)
    args=parser.parse_args(); print(json.dumps(compare(args.runner,args.cases)))


if __name__ == '__main__': main()
