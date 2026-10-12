"""Run a complete offline Drag sprint with local assets and authored physics.

This deterministic straight-line smoke check complements rendered UI checks;
it does not validate recovered force fidelity or object collision response.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from client.assets import Assets
from client.catalogue import Catalogue
from client.driving import Controls, Drive
from client.racing import TimeTrial
from client.track import decode_track
from client.world import load_world_vehicle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--vehicle', type=int, default=101)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assets = Assets(args.game)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    track_bytes = assets.paths['data/tracks/drag/tr.frd'].read_bytes()
    trial = TimeTrial(decode_track(track_bytes))
    world = load_world_vehicle(assets, catalogue, catalogue.vehicle(args.vehicle), track_bytes)
    drive = Drive(world, trial)
    for frame in range(60*120):
        drive.update(1/60, Controls(throttle=1))
        if drive.blocked:
            raise ValueError(f'missing terrain at frame {frame}, gate {trial.next_gate}')
        if not all(c.gap is not None and c.gap >= .02-1e-6 for c in drive.contacts):
            raise ValueError('wheel support clearance failed')
        if trial.finished:
            break
    if not trial.finished:
        raise ValueError(f'sprint did not finish; next gate {trial.next_gate}')
    result = dict(vehicle=args.vehicle, track='Drag', sprint_seconds=trial.elapsed,
                  distance_m=drive.distance, gates=len(trial.gates),
                  finish_pose=asdict(drive.pose), physics='authored bicycle model',
                  original_force_fidelity_verified=False, graphics_verified=False)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'Drag sprint finished: {trial.elapsed:.2f}s, {drive.distance:.1f}m, {len(trial.gates)} gates')


if __name__ == '__main__':
    main()
