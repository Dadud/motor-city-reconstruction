"""Compare external original part.fsh images to native RGBA checksums.

Prints only a summary; original pixel data is never saved.
"""
import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client.assets import Assets


def compare(executable: Path, root: Path) -> tuple[int, int]:
    assets = Assets(root)
    images = pixels = 0
    for path in assets.vehicles():
        textures = assets.load_textures(path)
        rows = subprocess.check_output(
            [str(executable.resolve()), str(assets.root),
             path.relative_to(assets.root).as_posix().lower()], text=True).splitlines()
        if len(rows) != len(textures):
            raise ValueError(f'{path.name}: texture count mismatch')
        for texture, row in zip(textures, rows):
            name, width, height, checksum = row.split()
            if (name, int(width), int(height)) != (
                    texture.name, texture.width, texture.height):
                raise ValueError(f'{path.name}: texture metadata mismatch')
            value = 14695981039346656037
            for byte in texture.rgba:
                value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
            if value != int(checksum):
                raise ValueError(f'{path.name}: decoded RGBA checksum mismatch')
            images += 1
            pixels += texture.width * texture.height
    return images, pixels


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_test_executable', type=Path)
    parser.add_argument('data_root', type=Path)
    args = parser.parse_args()
    images, pixels = compare(args.native_test_executable, args.data_root)
    print(f'Matched {images} original images and {pixels} RGBA pixels by FNV64 checksum')
