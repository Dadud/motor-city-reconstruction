"""Report real stock assets available to recovered driving and unresolved inputs."""
import argparse
import json
from pathlib import Path
from client.stock_driving_state import load_stock_driving_bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    parser.add_argument('--vehicle', type=int, default=101)
    parser.add_argument('--track', default='drag')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    bindings = load_stock_driving_bindings(args.game, args.vehicle, args.track)
    if args.output:
        # Output is explicitly external to the original asset installation.
        destination = args.output.resolve()
        if destination.is_relative_to(args.game.resolve()):
            parser.error('write the report outside the original game installation')
        destination.write_text(json.dumps(bindings.report(), indent=2)+'\n', encoding='utf-8')
    print(f'{bindings.vehicle_name} ({bindings.vehicle_id}): four decoded stock wheel assemblies')
    print('Recovered driving startup: unresolved')
    for group, reason in bindings.unresolved.items():
        print(f'{group}: {reason}')


if __name__ == '__main__':
    main()
