"""Compare the portable intake term with bounded original CPU emulation."""
import argparse
import json
import math
from pathlib import Path

from client.dyno import _SOURCE_SHA256, intake_rpm_correction
from tools.native_oracle import DynoOracle


def compare(executable):
    import unicorn
    oracle = DynoOracle(executable)
    calibrations = []
    for base, exponent in ((10, 1.3), (4, .5), (2, 3), (100, .5), (1, 1.428)):
        value = oracle.power(base, exponent)
        reference = math.pow(base, exponent)
        if not math.isclose(value, reference, rel_tol=1e-14, abs_tol=1e-14):
            raise ValueError('emulated power helper failed calibration')
        calibrations.append(dict(base=base, exponent=exponent, emulated=value,
                                 python_reference=reference))
    rows = []
    for mode in range(1, 7):
        for rpm in range(2000, 11001, 500):
            for factor in (.9, 1., 1.1):
                native = oracle.intake_correction(mode, rpm, factor)
                portable = intake_rpm_correction(mode, rpm, factor)
                rows.append(dict(mode=mode, rpm=rpm, flow_factor=factor,
                                 emulated=native, portable=portable, difference=portable-native))
    return dict(emulator=f'unicorn {unicorn.__version__}', fpu_control_word='0x27f',
        execution_range=['0x479c5e', '0x479df6'], target_sha256=_SOURCE_SHA256,
        power_calibrations=calibrations, exact_matches=sum(row['difference'] == 0 for row in rows),
        samples=rows, full_game_runtime_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.executable)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f"{result['exact_matches']}/{len(result['samples'])} intake samples match exactly")
    if result['exact_matches'] != len(result['samples']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
