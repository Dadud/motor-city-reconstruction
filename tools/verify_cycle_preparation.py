"""Compare coupled cycle preparation and exhaust waves to native CPU ranges."""
import argparse
from dataclasses import astuple
import json
from pathlib import Path
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.dyno import _SOURCE_SHA256, load_flow_templates
from client.dyno_solver import cylinder_geometry, valve_events
from client.thermodynamics import (charge_temperature, cycle_preparation,
                                   exhaust_parameters, exhaust_phase_factor,
                                   exhaust_wave_value, intake_boundary)
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
    rows, synthetic, unsupported = [], [], []
    counts = dict(temperature=0, preparation=0, phase_factor=0, wave=0, intake_boundary=0)

    def compare_intake(geometry, rpm, capacity, code, mode, boost=0):
        actual = astuple(intake_boundary(geometry, rpm, capacity, code, mode, boost))
        expected = oracle.intake_boundary(geometry, rpm, capacity, code, mode, boost)
        if actual != expected:
            raise ValueError(f'intake boundary differs: {rpm}/{capacity}/{code}/{mode}/{boost}')
        counts['intake_boundary'] += 3
        return actual

    def compare_temperature(mode, rpm):
        temperature = charge_temperature(mode, rpm)
        if temperature != oracle.charge_temperature(mode, rpm):
            raise ValueError(f'temperature differs: {mode}/{rpm}')
        counts['temperature'] += 1
        return temperature

    def compare_preparation(rpm, temperature, exhaust):
        actual = cycle_preparation(rpm, temperature, exhaust)
        expected = oracle.cycle_preparation(rpm, temperature, exhaust)
        if astuple(actual) != expected:
            raise ValueError(f'cycle preparation differs: {rpm}/{temperature}/{exhaust}')
        counts['preparation'] += 3
        return actual

    def compare_wave(angle, start, factor, rpm, exhaust, scale, previous=0, boost=0):
        actual = exhaust_wave_value(angle, start, factor, rpm, exhaust, scale, previous, boost)
        expected = oracle.exhaust_wave_value(angle, start, factor, rpm, exhaust, scale, previous, boost)
        if actual != expected:
            raise ValueError(f'exhaust wave differs: {angle}/{start}/{rpm}/{exhaust}: {actual} != {expected}')
        counts['wave'] += 1
        return actual

    for mode in (1, 9, 10, 19, 20, 25):
        for rpm in (2000, 5499.999, 5500, 5500.001, 11000):
            synthetic.append(dict(mode=mode, rpm=rpm, temperature=compare_temperature(mode, rpm)))
    geometry = cylinder_geometry(4, 3.5, 9, 8)
    for code in (2, 4):
        for mode in range(1, 7):
            for capacity in (300, 500, 1000):
                for rpm in (2000, 5500, 11000):
                    for boost in (0, 5):
                        synthetic.append(dict(carb_code=code, intake_mode=mode, capacity=capacity,
                            rpm=rpm, boost=boost, intake=compare_intake(geometry, rpm, capacity, code, mode, boost)))
    for mode in range(1, 8):
        for rpm in range(2000, 11001, 500):
            exhaust = exhaust_parameters(mode, rpm, 1)
            for temperature in (200, 540, 584.56, 2000):
                compare_preparation(rpm, temperature, exhaust)
        exhaust = exhaust_parameters(mode, exhaust.reference_rpm, 1)
        rpm = exhaust.reference_rpm
        scale = cycle_preparation(rpm, 540, exhaust).exhaust_wave_scale
        for angle in (0, 90, 179.9999, 180, 180.0001, 270, 359.9999, 360, 360.0001, 450, 720):
            for boost in (0, 1):
                synthetic.append(dict(exhaust_mode=mode, angle=angle, boost=boost,
                    wave=compare_wave(angle, 0, 1, rpm, exhaust, scale, 12.34, boost)))
    for identifier in catalogue.vehicles:
        try:
            record = catalogue.stock_dyno_record(catalogue.vehicle(identifier), templates)
        except ValueError as error:
            unsupported.append(dict(vehicle=identifier, reason=str(error)))
            continue
        temperature_mode = struct.unpack_from('<h', record, 0x2dc)[0]
        geometry = cylinder_geometry(*struct.unpack_from('<2f', record, 0x8c),
                                    struct.unpack_from('<f', record, 0xa0)[0],
                                    struct.unpack_from('<h', record, 0x94)[0])
        capacity, code = struct.unpack_from('<2h', record, 0xa4)
        intake_mode = struct.unpack_from('<h', record, 0x6e)[0]
        exhaust_mode = struct.unpack_from('<h', record, 0x7a)[0]
        flow = struct.unpack_from('<f', record, 0x7c)[0]
        start = valve_events(record).angle_a8
        factor = exhaust_phase_factor(start)
        if factor != oracle.exhaust_phase_factor(start):
            raise ValueError(f'phase factor differs: {identifier}')
        counts['phase_factor'] += 1
        samples = []
        for rpm in range(2000, 11001, 500):
            exhaust = exhaust_parameters(exhaust_mode, rpm, flow)
            temperature = compare_temperature(temperature_mode, rpm)
            prepared = compare_preparation(rpm, temperature, exhaust)
            waves = [compare_wave(angle, start, factor, rpm, exhaust, prepared.exhaust_wave_scale)
                     for angle in (0, 90, 180, 270, 360, 450, 540, 720)]
            intake = compare_intake(geometry, rpm, capacity, code, intake_mode)
            samples.append(dict(rpm=rpm, temperature=temperature, preparation=astuple(prepared),
                                waves=waves, intake=intake))
        rows.append(dict(vehicle=identifier, start_angle=start, phase_factor=factor, samples=samples))
    result = dict(target_sha256=_SOURCE_SHA256, matched_fields=counts,
                  rows=rows, synthetic=synthetic, unsupported=unsupported,
                  full_pressure_loop_verified=False, original_game_runtime_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{len(rows)} stock engines: {sum(counts.values())} exact cycle/exhaust matches {counts}')


if __name__ == '__main__':
    main()
