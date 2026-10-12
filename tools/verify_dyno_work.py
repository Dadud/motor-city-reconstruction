"""Compare portable work conversion with original CPU-emulated solver stages."""
import argparse
import json
from pathlib import Path
import struct
from dataclasses import astuple

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import (cam_profiles, cylinder_geometry, flow_coefficients,
                                valve_events, work_outputs)
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--geometry-only', action='store_true')
    args = parser.parse_args()
    assets = Assets(args.game)
    executable = assets.paths['mcity.exe']
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    templates = load_flow_templates(executable)
    oracle = DynoOracle(executable)
    rows, unsupported = [], []
    offsets = (0xc4, 0x110, 0x1f4, 0x240, 0x28c)
    for identifier in catalogue.vehicles:
        try:
            inputs = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle_id=identifier, reason=str(error)))
            continue
        geometry = astuple(cylinder_geometry(
            struct.unpack_from('<f', inputs, 0x8c)[0],
            struct.unpack_from('<f', inputs, 0x90)[0],
            struct.unpack_from('<f', inputs, 0xa0)[0],
            struct.unpack_from('<h', inputs, 0x94)[0]))
        if geometry != oracle.solver_geometry(inputs):
            raise ValueError(f'{identifier}: cylinder geometry differs')
        events = astuple(valve_events(inputs))
        if events != oracle.solver_valve_events(inputs):
            raise ValueError(f'{identifier}: valve events differ')
        flow = astuple(flow_coefficients(inputs))
        if flow != oracle.solver_flow_coefficients(inputs):
            raise ValueError(f'{identifier}: flow coefficients differ')
        profiles = tuple(astuple(p) for p in cam_profiles(inputs))
        if profiles != oracle.solver_cam_profiles(inputs):
            raise ValueError(f'{identifier}: cam profiles differ')
        if args.geometry_only:
            rows.append(dict(vehicle_id=identifier, geometry=geometry,
                             valve_events=events, flow_coefficients=flow,
                             cam_profiles=profiles))
            continue
        output, stages = oracle.solver_work_stages(inputs)
        if len(stages) != 19:
            raise ValueError(f'{identifier}: expected nineteen work stages')
        samples = []
        for index, stage in enumerate(stages):
            actual = work_outputs(*stage)
            expected = tuple(struct.unpack_from('<f', output, offset+index*4)[0]
                             for offset in offsets)
            if actual != expected:
                raise ValueError(f'{identifier} at {stage[0]}: {actual} != {expected}')
            samples.append(dict(inputs=stage, outputs=actual))
        rows.append(dict(vehicle_id=identifier, geometry=geometry,
                         valve_events=events, flow_coefficients=flow,
                         cam_profiles=profiles, samples=samples))
    result = dict(target_sha256=_SOURCE_SHA256, emulator='unicorn 2.1.4',
                  fpu_control_word='0x27f', stage_address='0x47b2b7',
                  output_offsets=list(offsets), matched_vehicles=len(rows),
                  matched_fields=0 if args.geometry_only else len(rows)*19*5,
                  matched_geometry_fields=len(rows)*6,
                  matched_valve_event_fields=len(rows)*6,
                  matched_flow_fields=len(rows)*21,
                  matched_cam_fields=len(rows)*12,
                  geometry_only=args.geometry_only, unsupported=unsupported, rows=rows,
                  portable_integration_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} vehicles: {result["matched_fields"]} output fields, '
          f'{len(rows)*6} geometry fields match exactly')


if __name__ == '__main__':
    main()
