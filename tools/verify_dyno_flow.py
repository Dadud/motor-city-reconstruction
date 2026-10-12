"""Compare native interpolation for every distinct supported stock flow table."""
import argparse
import json
import math
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import flow_coefficients, interpolate_flow
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    exe = assets.paths['mcity.exe']
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    templates, oracle = load_flow_templates(exe), DynoOracle(exe)
    tables, unsupported = {}, []
    for identifier in catalogue.vehicles:
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle_id=identifier, reason=str(error)))
            continue
        flow = flow_coefficients(record)
        for first, offset, coefficients in ((True, 0x39c, flow.series_374),
                                            (False, 0x34c, flow.series_324)):
            points = struct.unpack_from('<10f', record, offset)
            tables.setdefault((first, points, coefficients), []).append(identifier)
    rows, total, exact, maximum = [], 0, 0, 0
    print(f'Checking {len(tables)} distinct stock tables', flush=True)
    for (first, points, coefficients), identifiers in tables.items():
        active = [p for p in points if p > 0]
        lifts = sorted(set([0, active[0]*.5, active[-1]*1.1, *active,
                            *((a+b)*.5 for a, b in zip(active, active[1:]))]))
        samples = []
        for lift in lifts:
            actual = interpolate_flow(lift, points, coefficients)
            expected = oracle.interpolate_flow(lift, points, coefficients, first=first)
            error = abs(actual-expected)
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f'{identifiers}/{first}/{lift}: interpolation differs')
            if struct.pack('<f', actual) != struct.pack('<f', expected):
                raise ValueError('interpolation float32 differs')
            total += 1
            exact += actual == expected
            maximum = max(maximum, error)
            samples.append(dict(lift=lift, portable=actual, original=expected))
        rows.append(dict(first=first, vehicle_ids=identifiers, points=points,
                         coefficients=coefficients, samples=samples))
    result = dict(target_sha256=_SOURCE_SHA256, emulator='unicorn 2.1.4',
                  fpu_control_word='0x27f', rows=rows, unsupported=unsupported,
                  matched_float32=total, exact_double=exact,
                  maximum_absolute_error=maximum, integration_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{total} float32 matches, {exact} exact doubles, maximum error {maximum}')


if __name__ == '__main__':
    main()
