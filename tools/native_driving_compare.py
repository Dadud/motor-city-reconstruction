"""Run all newly recovered driving comparison corpora against a native build."""
import argparse
import importlib
import json
from pathlib import Path


def verify(directory):
    directory=Path(directory)
    results={}
    for name in ('driving_engine_rpm','drivetrain_coupling','wheel_force_correction',
                 'brake_thermal','brake_forces','wheel_spin','combined_slip','vehicle_update',
                 'engine_update','engine_torque_update','engine_pipeline','body_vertical_load','body_resistance','air_density',
                 'vehicle_preparation','scheduler',
                 'wind','drafting','body_environment','control_update','drivetrain_links',
                 'collision_response','collision_impulse','body_moments'):
        runner=directory/f'mco_{name}_compare'
        if not runner.is_file(): runner=runner.with_suffix('.exe')
        module=importlib.import_module(f'tools.native_{name}_compare')
        results[name]=module.verify(runner)
        if name=='engine_update':
            results['engine_system_update']=module.verify(runner,vehicle_system=True)
    runner=directory/'mco_support_prediction_compare'
    if not runner.is_file(): runner=runner.with_suffix('.exe')
    results['support_prediction']=importlib.import_module('tools.native_support_prediction_compare').verify(runner)
    runner=directory/'mco_track_plane_compare'
    if not runner.is_file(): runner=runner.with_suffix('.exe')
    results['track_plane']=importlib.import_module('tools.native_track_plane_compare').verify(runner)
    runner=directory/'mco_track_surface_sample_compare'
    if not runner.is_file(): runner=runner.with_suffix('.exe')
    results['track_surface_sample']=importlib.import_module('tools.native_track_surface_sample_compare').verify(runner)
    orientation=directory/'mco_wheel_force_orientation_compare'
    if not orientation.is_file(): orientation=orientation.with_suffix('.exe')
    results['wheel_force_orientation']=importlib.import_module('tools.native_body_moments_compare').verify(orientation,'orientation')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory')
    print(json.dumps(verify(parser.parse_args().directory)))
