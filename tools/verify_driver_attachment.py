"""Compare the special driver and driver-head branch of original 0x52df00."""
import argparse
import struct
from pathlib import Path

from client.assets import Assets
from client.fce import decode
from client.scene import DRIVER_MODEL_BY_VARIANT
from client.tire_response import f32
from tools.native_oracle import DynoOracle
from tools.viv import read_member


def _body_image(origin):
    image = bytearray(0x2038)
    struct.pack_into('<I', image, 0x11c, 1)
    struct.pack_into('<3f', image, 0x120, *origin)
    image[0xe28:0xe28+10] = b':PPdriver\0'
    return bytes(image)


def verify(executable, game):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    body, node, driver, render = base+0x10000, base+0x2000, base+0x30000, base+0x50000
    marker_origin = (2.0, 3.0, 4.0)
    assets = Assets(game)
    reports = []

    for variant, archive in enumerate(DRIVER_MODEL_BY_VARIANT):
        path = assets.paths.get(f'data/models/{archive}.viv')
        if path is None:
            raise ValueError(f'variant {variant}: missing {archive}.viv')
        source = read_member(path, 'part.fce')
        model = decode(source)
        driver_index = next((i for i,p in enumerate(model.parts) if p.name == ':PHdriver'), None)
        head_index = next((i for i,p in enumerate(model.parts) if p.name == ':PHdriverhead'), None)
        if driver_index is None or head_index is None:
            raise ValueError(f'variant {variant}: {archive} lacks driver meshes')
        driver_origin = model.parts[driver_index].origin
        head_origin = model.parts[head_index].origin
        expected = bytearray(source)
        struct.pack_into('<3f', expected, 0x120+driver_index*12, *marker_origin)
        head_target = tuple(f32(f32(head-driver)+marker) for marker,head,driver in
                            zip(marker_origin,head_origin,driver_origin))
        struct.pack_into('<3f', expected, 0x120+head_index*12, *head_target)

        cpu.mem_write(body, _body_image(marker_origin))
        cpu.mem_write(driver, source)
        cpu.mem_write(render, bytes(0x400))
        cpu.mem_write(node, bytes(0x400))
        cpu.mem_write(node, struct.pack('<II', 0, driver))
        cpu.mem_write(node+0x18, struct.pack('<I', 0))       # empty class prefix
        cpu.mem_write(node+0x338, struct.pack('<I', 0x80e9)) # native driver class
        oracle.call(0x52df00, (body, node, render, 0, 0),
                    instruction_limit=1_000_000)
        count, = struct.unpack('<I', cpu.mem_read(render, 4))
        records = bytes(cpu.mem_read(render+4, 72))
        observed_image = bytes(cpu.mem_read(driver, len(source)))
        if count != 2 or observed_image != bytes(expected):
            differences = [i for i, (left, right) in enumerate(zip(observed_image, expected))
                           if left != right]
            raise AssertionError((variant, archive, count, differences[:16],
                [(i, observed_image[i:i+4].hex(), expected[i:i+4].hex())
                 for i in differences[:8]]))
        for record_index, (part_index, sort_type) in enumerate(
                ((driver_index, 0x11), (head_index, 0x10))):
            entry = records[record_index*36:(record_index+1)*36]
            model_pointer, = struct.unpack_from('<I', entry, 4)
            selected_part, = struct.unpack_from('<H', entry, 12)
            flags, = struct.unpack_from('<I', entry, 16)
            record_type, = struct.unpack_from('<I', entry, 20)
            if (model_pointer != driver or selected_part != part_index or
                    flags != 0x81 or record_type != sort_type):
                raise AssertionError((variant, archive, record_index,
                    model_pointer, selected_part, flags, record_type))
        reports.append((variant, archive))
    return dict(cases=len(reports), max_error=0, original_entry='0x52df00',
        scope='all 33 original driver selector archives; complete driver FCE origins and both render records compared')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('game', type=Path)
    args = parser.parse_args()
    print(verify(args.executable, args.game))


if __name__ == '__main__':
    main()
