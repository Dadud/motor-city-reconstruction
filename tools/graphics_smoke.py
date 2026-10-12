"""Exercise the real OpenGL client with generated geometry and no game assets."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from PIL import Image

from client.fce import HEADER


def triangle_archive():
    geometry = bytearray(HEADER+128)
    struct.pack_into('<4I', geometry, 0, 0x101015, 0, 1, 3)
    struct.pack_into('<3I', geometry, 0x14, 0, 36, 72)
    struct.pack_into('<I', geometry, 0x11c, 1)
    struct.pack_into('<I', geometry, 0x520, 3)
    struct.pack_into('<I', geometry, 0x720, 1)
    geometry[0xe28:0xe2e] = b':Hbody'
    struct.pack_into('<9f', geometry, HEADER, -1, -1, 0, 1, -1, 0, 0, 1, 0)
    struct.pack_into('<9f', geometry, HEADER+36, 0, 0, 1, 0, 0, 1, 0, 0, 1)
    struct.pack_into('<4I', geometry, HEADER+72, 0, 0, 1, 2)
    struct.pack_into('<6f', geometry, HEADER+104, 0, 1, .5, 0, 0, 1)
    name = b'part.fce\0'
    offset = 24+len(name)
    return (struct.pack('>4sIII', b'BIGF', offset+len(geometry), 1, offset)+
            struct.pack('>II', offset, len(geometry))+name+geometry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='motor-city-graphics-') as temporary:
        root = Path(temporary)
        models = root/'Data'/'Models'
        models.mkdir(parents=True)
        (models/'smoke.viv').write_bytes(triangle_archive())
        subprocess.run([sys.executable, '-m', 'client.app', '--data', str(root),
                        '--model', 'smoke.viv', '--screenshot', str(output)],
                       check=True, timeout=60)
    report = json.loads(output.with_suffix('.runtime.json').read_text(encoding='utf-8'))
    if report['triangles'] != 1 or not report['renderer']:
        raise ValueError('graphics smoke check did not render the generated triangle')
    with Image.open(output) as captured:
        width, height = captured.size
        middle = captured.convert('RGB').crop((width//3, height//3, width*2//3, height*2//3))
        visible = sum(min(pixel) > 50 for pixel in middle.get_flattened_data())
        if visible < 100:
            raise ValueError('generated geometry is absent from the central framebuffer')
    print(f"Graphics smoke passed: {report['platform']} / {report['renderer']}")


if __name__ == '__main__':
    main()
