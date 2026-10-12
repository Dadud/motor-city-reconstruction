"""Verify valve mass exchange with native probes and sampled full-solver states."""
import argparse
from dataclasses import astuple
import json
from pathlib import Path

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.thermodynamics import (IntakeExchange, intake_mass_exchange,
                                   exhaust_mass_transfer, intake_pressure_feedback)
from tools.native_oracle import DynoOracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--vehicles', nargs='+', type=int, help='default: all supported stock engines')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    exe = assets.paths['mcity.exe']
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    oracle, templates = DynoOracle(exe), load_flow_templates(exe)
    synthetic, rows, unsupported = [], [], []
    matched, forward, reverse, closed = 0, 0, 0, 0
    feedback = IntakeExchange(.1, .5, .2, 1000, .01)
    for pressure in (5, 14.7, 44.1, 80, 150):
        for temperature in (540, 2000, 4000):
            for boundary in (5, 14.7, 35, 80, 150):
                for area in (0, .01, 1.2, 3):
                    for rpm in (2000, 5500, 11000):
                        for incoming_temperature in (540, 584.56):
                            intake = (pressure, temperature, boundary, incoming_temperature, area, rpm)
                            exhaust = (pressure, temperature, boundary, area, rpm)
                            actual = astuple(intake_mass_exchange(*intake, previous=feedback))
                            expected = oracle.intake_mass_exchange(*intake, previous=feedback)
                            delta = exhaust_mass_transfer(*exhaust)
                            pressure_feedback = intake_pressure_feedback(boundary, area, .13, feedback, 2.3)
                            if actual != expected or delta != oracle.exhaust_mass_transfer(*exhaust):
                                raise ValueError(f'synthetic transfer differs: {intake}: {actual} != {expected}')
                            if pressure_feedback != oracle.intake_pressure_feedback(boundary, area, .13, feedback, 2.3):
                                raise ValueError(f'synthetic pressure feedback differs: {intake}')
                            matched += 7
                            synthetic.append(dict(intake_inputs=intake, intake_output=actual,
                                                  exhaust_output=delta, pressure_feedback=pressure_feedback))
    for identifier in (args.vehicles or catalogue.vehicles):
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle=identifier, reason=str(error)))
            continue
        _, stages, counts = oracle.solver_mass_exchange_stages(record)
        if len(counts) != 19 or not stages:
            raise ValueError(f'{identifier}: missing full-solver RPM samples')
        for index, stage in enumerate(stages):
            actual = astuple(intake_mass_exchange(*stage['intake_inputs'],
                             previous=IntakeExchange(0, *stage['feedback'])))
            exhaust = exhaust_mass_transfer(*stage['exhaust_inputs'])
            source = stage['pressure_feedback']
            boundary, area, scale, wave = source['inputs']
            pressure_feedback = intake_pressure_feedback(boundary, area, scale,
                IntakeExchange(0, 0, *source['previous']), wave)
            if actual != stage['intake_output'] or exhaust != stage['exhaust_output']:
                raise ValueError(f'{identifier}/{index}: sampled transfer differs: {actual} != {stage["intake_output"]}; exhaust {exhaust} != {stage["exhaust_output"]}')
            if pressure_feedback != stage['intake_inputs'][2]:
                raise ValueError(f'{identifier}/{index}: sampled pressure feedback differs')
            matched += 7
            for delta in (actual[0], exhaust):
                forward += delta > 0
                reverse += delta < 0
                closed += delta == 0
        rows.append(dict(vehicle=identifier, samples=stages, original_calls_by_rpm=counts))
        print(f'{identifier}: {len(stages)} full-solver stage pairs matched', flush=True)
    result = dict(target_sha256=_SOURCE_SHA256, matched_float32=matched,
                  synthetic=synthetic, rows=rows, unsupported=unsupported,
                  sampled_delta_signs=dict(positive=forward, negative=reverse, zero=closed),
                  sampling_stride=64, maximum_samples_per_rpm=32,
                  portable_full_solver_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} stock engines: {matched} exact mass-exchange field matches')


if __name__ == '__main__':
    main()
