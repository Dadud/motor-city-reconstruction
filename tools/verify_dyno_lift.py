"""Compare portable valve lift with bounded original instruction ranges."""
import argparse
from dataclasses import astuple
import json
import math
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import cam_profiles, valve_events, valve_lift
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    executable = assets.paths['mcity.exe']
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    templates = load_flow_templates(executable)
    oracle = DynoOracle(executable)
    rows, unsupported = [], []
    maximum_error, exact_double, total = 0, 0, 0
    for identifier in catalogue.vehicles:
        try:
            inputs = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle_id=identifier, reason=str(error)))
            continue
        events = valve_events(inputs)
        samples = []
        for index, (profile, start, end) in enumerate(zip(cam_profiles(inputs),
                (events.angle_a8, events.angle_b0), (events.angle_ac, events.angle_b4))):
            for fraction in (.001, .05, .15, .25, .5, .75, .85, .95, .999):
                angle = struct.unpack('<f', struct.pack('<f', start+(end-start)*fraction))[0]
                actual = valve_lift(profile, start, end, angle)
                expected = oracle.valve_lift(astuple(profile), start, angle, first=index == 0)
                error = abs(actual-expected)
                if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(f'{identifier}/{index}/{angle}: lift differs')
                if struct.pack('<f', actual) != struct.pack('<f', expected):
                    raise ValueError(f'{identifier}/{index}/{angle}: float32 lift differs')
                maximum_error = max(maximum_error, error)
                exact_double += actual == expected
                total += 1
                samples.append(dict(profile=index, angle=angle, portable=actual,
                                    original=expected))
        rows.append(dict(vehicle_id=identifier, samples=samples))
    result = dict(target_sha256=_SOURCE_SHA256, emulator='unicorn 2.1.4',
                  fpu_control_word='0x27f', matched_float32=total,
                  exact_double=exact_double, maximum_absolute_error=maximum_error,
                  rows=rows, unsupported=unsupported, integration_verified=False,
                  original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} engines: {total} float32 matches; '
          f'{exact_double} exact doubles; maximum error {maximum_error}')


if __name__ == '__main__':
    main()
