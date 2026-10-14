"""Run all newly recovered driving comparison corpora against a native build."""
import argparse
import importlib
import json
from pathlib import Path


def verify(directory):
    directory=Path(directory)
    results={}
    for name in ('driving_engine_rpm','drivetrain_coupling','wheel_force_correction',
                 'brake_thermal','collision_response','collision_impulse','body_moments'):
        runner=directory/f'mco_{name}_compare'
        if not runner.is_file(): runner=runner.with_suffix('.exe')
        module=importlib.import_module(f'tools.native_{name}_compare')
        results[name]=module.verify(runner)
    orientation=directory/'mco_wheel_force_orientation_compare'
    if not orientation.is_file(): orientation=orientation.with_suffix('.exe')
    results['wheel_force_orientation']=importlib.import_module('tools.native_body_moments_compare').verify(orientation,'orientation')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory')
    print(json.dumps(verify(parser.parse_args().directory)))
