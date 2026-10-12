"""Compare portable exhaust preparation with all valid native branches."""
import argparse
from dataclasses import astuple
import json
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.thermodynamics import exhaust_parameters
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    executable = assets.paths['mcity.exe']
    oracle, templates = DynoOracle(executable), load_flow_templates(executable)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    cases, unsupported = [], []

    def compare(mode, rpm, factor, vehicle=None):
        actual = astuple(exhaust_parameters(mode, rpm, factor))
        expected = oracle.exhaust_parameters(mode, rpm, factor)
        if actual != expected:
            raise ValueError(f'{vehicle}/{mode}/{rpm}/{factor}: {actual} != {expected}')
        cases.append(dict(vehicle=vehicle, mode=mode, rpm=rpm, flow_factor=factor, fields=actual))

    for mode in range(1, 8):
        for rpm in range(2000, 11001, 500):
            for factor in (.9, 1, 1.1):
                compare(mode, rpm, factor)
    supported = 0
    for identifier in catalogue.vehicles:
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle=identifier, reason=str(error)))
            continue
        mode = struct.unpack_from('<h', record, 0x7a)[0]
        factor = struct.unpack_from('<f', record, 0x7c)[0]
        for rpm in range(2000, 11001, 500):
            compare(mode, rpm, factor, identifier)
        supported += 1
    result = dict(target_sha256=_SOURCE_SHA256, supported_engines=supported,
                  matched_float32=len(cases)*4, cases=cases, unsupported=unsupported,
                  full_pressure_loop_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{supported} stock engines / all 7 modes: {len(cases)*4} exact exhaust-field matches')


if __name__ == '__main__':
    main()
