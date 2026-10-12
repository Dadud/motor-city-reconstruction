"""Compare portable cylinder initialization with bounded native instructions."""
import argparse
from dataclasses import astuple
import json
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import cylinder_geometry, valve_events
from client.thermodynamics import initial_cylinder_state
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
    rows, unsupported = [], []
    for identifier in catalogue.vehicles:
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle_id=identifier, reason=str(error)))
            continue
        bore, stroke = struct.unpack_from('<2f', record, 0x8c)
        geometry = cylinder_geometry(bore, stroke,
                                     struct.unpack_from('<f', record, 0xa0)[0],
                                     struct.unpack_from('<h', record, 0x94)[0])
        angle = valve_events(record).angle_a8
        samples = []
        for pressure in (44.1, 15, 80):
            actual = astuple(initial_cylinder_state(geometry, stroke, angle, pressure))
            expected = oracle.initial_cylinder_state(geometry, stroke, angle, pressure)
            if actual != expected:
                raise ValueError(f'{identifier}/{pressure}: {actual} != {expected}')
            samples.append(dict(pressure=pressure, state=actual))
        rows.append(dict(vehicle_id=identifier, samples=samples))
    count = len(rows)*3*7
    result = dict(target_sha256=_SOURCE_SHA256, matched_float32=count,
                  rows=rows, unsupported=unsupported, synthetic_pressure_inputs=True,
                  full_integration_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} stock engines: {count} exact cylinder-state field matches')


if __name__ == '__main__':
    main()
