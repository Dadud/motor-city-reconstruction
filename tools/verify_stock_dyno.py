"""Capture a stock-derived core dyno result through bounded CPU emulation."""
import argparse
import json
import math
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import mechanical_loss
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--vehicle', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    executable = assets.paths.get('mcity.exe')
    database = assets.paths.get('data/db/online.mdb')
    if executable is None or database is None:
        parser.error('requires the local mcity.exe and Data/DB/Online.mdb')
    catalogue = Catalogue.load(database)
    vehicle = catalogue.vehicle(args.vehicle)
    templates = load_flow_templates(executable)
    inputs = catalogue.stock_dyno_record(vehicle, templates)
    oracle = DynoOracle(executable)
    native_inputs = oracle.builder_inputs(catalogue.stock_dyno_assembled(
        vehicle, templates))
    if inputs != native_inputs:
        raise ValueError('portable record differs from the emulated original builder')
    outputs = oracle.solver(inputs)
    stroke = struct.unpack_from('<f', inputs, 0x90)[0]
    losses = struct.unpack_from('<19f', outputs, 0x28c)
    portable_losses = tuple(mechanical_loss(rpm, stroke)
                           for rpm in range(2000, 11001, 500))
    if losses != portable_losses:
        raise ValueError('portable mechanical loss differs from original solver')
    torque = struct.unpack_from('<19f', outputs, 0x110)
    if not all(math.isfinite(value) and value >= 0 for value in torque) or not max(torque) > 0:
        raise ValueError('emulated stock core returned invalid or all-zero torque samples')
    result = dict(vehicle_id=vehicle.branded_id, vehicle_name=vehicle.name,
        target_sha256=_SOURCE_SHA256, input_hex=inputs.hex(), output_hex=outputs.hex(),
        core_torque_samples=torque, rpm_samples=list(range(2000, 11001, 500)),
        emulator='unicorn 2.1.4', fpu_control_word='0x27f', stock_assembly_core_only=True,
        original_game_runtime_verified=False, final_curve_complete=False,
        native_builder_record_equal=True, same_assembled_fields=True,
        component_loader_equivalence_proven=False)
    result['mechanical_loss_samples'] = losses
    result['portable_mechanical_loss_equal'] = True
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{vehicle.name}: 19 finite core samples, maximum {max(torque):.6f}')


if __name__ == '__main__':
    main()
