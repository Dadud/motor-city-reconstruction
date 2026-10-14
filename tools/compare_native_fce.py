"""Compare native FCE decoding against Python using external installed vehicles.

Only summaries are printed; proprietary vertex positions are never saved.
Run from the repository root with a locally built mco_fce_compare executable.
"""
import argparse
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client.assets import Assets


def compare(executable: Path, root: Path) -> tuple[int, int]:
    assets = Assets(root)
    vertex_count = 0
    paths = assets.vehicles()
    for path in paths:
        model = assets.load_vehicle(path)
        lines = subprocess.check_output(
            [str(executable.resolve()), str(root.resolve()),
             path.relative_to(assets.root).as_posix().lower()], text=True).splitlines()
        version, parts = map(int, lines[0].split())
        if version != model.version or parts != len(model.parts):
            raise ValueError(f'{path.name}: model metadata mismatch')
        cursor = 1
        for part in model.parts:
            row = lines[cursor].split()
            cursor += 1
            if (row[0] != part.name or int(row[1]) != len(part.vertices)
                    or int(row[2]) != len(part.triangles)):
                raise ValueError(f'{path.name}: part metadata mismatch')
            pairs = zip(map(float, row[3:]), part.origin)
            if len(row[3:]) != 3 or not all(
                    math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-7) for a, b in pairs):
                raise ValueError(f'{path.name}: part origin mismatch')
            for position in part.vertices:
                row = lines[cursor].split()
                cursor += 1
                pairs = zip(map(float, row), position)
                if len(row) != 3 or not all(
                        math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-7) for a, b in pairs):
                    raise ValueError(f'{path.name}: vertex position mismatch')
            vertex_count += len(part.vertices)
        if cursor != len(lines):
            raise ValueError(f'{path.name}: unexpected native output')
    return len(paths), vertex_count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('data_root', type=Path)
    args = parser.parse_args()
    cars, vertices = compare(args.executable, args.data_root)
    print(f'Compared {cars} original archives and {vertices} local vertex positions')
