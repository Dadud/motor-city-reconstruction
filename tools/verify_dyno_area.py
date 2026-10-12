"""Verify coupled airflow area on supported stock engine input fields."""
import argparse
import json
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import (airflow_area, cam_profiles, flow_coefficients,
                                valve_events, valve_lift)
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
    rows, unsupported, count = [], [], 0
    for identifier in catalogue.vehicles:
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle_id=identifier, reason=str(error)))
            continue
        events, flow = valve_events(record), flow_coefficients(record)
        samples = []
        branches = ((events.angle_a8, events.angle_ac, 0x39c, flow.series_374,
                     events.exhaust_size),
                    (events.angle_b0, events.angle_b4, 0x34c, flow.series_324,
                     events.intake_size))
        for index, (profile, branch) in enumerate(zip(cam_profiles(record), branches)):
            start, end, offset, coefficients, size = branch
            points = struct.unpack_from('<10f', record, offset)
            for fraction in (.05, .5, .95):
                angle = struct.unpack('<f', struct.pack('<f', start+(end-start)*fraction))[0]
                lift = valve_lift(profile, start, end, angle)
                for ratio in (.5, 1, 1.8929, 2, 4):
                    actual = airflow_area(lift, points, coefficients, size,
                                          pressure_ratio=None if index == 0 else ratio)
                    expected = oracle.airflow_area(lift, points, coefficients, size,
                                                   first=index == 0, pressure_ratio=ratio)
                    if actual != expected:
                        raise ValueError(f'{identifier}/{index}/{angle}/{ratio}: area differs')
                    count += 1
                    samples.append(dict(branch=index, angle=angle, lift=lift,
                                         ratio=ratio, area=actual))
        rows.append(dict(vehicle_id=identifier, samples=samples))
    result = dict(target_sha256=_SOURCE_SHA256, emulator='unicorn 2.1.4',
                  fpu_control_word='0x27f', matched_float32=count, rows=rows,
                  unsupported=unsupported, synthetic_pressure_ratios=True,
                  full_integration_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} stock engines: {count} exact float32 airflow-area matches')


if __name__ == '__main__':
    main()
