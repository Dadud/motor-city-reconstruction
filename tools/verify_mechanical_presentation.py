"""Compare 0x52c2e0's model-source and display-string writes."""
import argparse
from pathlib import Path
import struct

from client.mechanical_parts import (transfer_mechanical_physics,
                                     transfer_mechanical_presentation,
                                     expand_mechanical_parts)
from tools.native_oracle import DynoOracle
from tools.installation_check_cases import CheckOracle

MODEL_PREFIX_TABLE = 0x00a52d48
MODEL_PREFIX_INDEX = 15
MODEL_PREFIX_STRIDE = 0x104


def _slot(key, manufacturer, brand, name):
    image = bytearray(0x63c)
    for offset, end, value in ((0x387, 0x390, key), (0x390, 0x398, manufacturer),
                               (0x2c7, 0x307, brand), (0x307, 0x387, name)):
        if offset == 0x390:
            if len(value) > end - offset:
                raise ValueError('test string does not fit its source field')
            image[offset:offset + len(value)] = value
        else:
            if len(value) >= end - offset:
                raise ValueError('test string does not fit its source field')
            image[offset:offset + len(value)] = value
            image[offset + len(value)] = 0
    return bytes(image)


def _cases():
    yield _slot(b'', b'', b'EA', b'Generic Suspension'), 10, 'empty model source'
    yield _slot(b'.factory', b'Ford', b'Ford', b'32 V-8 Coupe'), 0, 'literal dotted model source'
    yield _slot(b'32ford', b'FORDMCO1', b'Ford', b'32 V-8 Coupe'), 5, 'prefixed VIV model path'
    yield _slot(b'longkey1', b'EA', b'X' * 63, b'Y' * 80), 11, 'bounded eight-byte key and display buffer'


def _initialize_model_prefix(oracle, installation_root):
    helper = CheckOracle(oracle, installation_root, real_formatter=True)
    helper.seed = 19  # successful registry queries and the level-2 CD-scan bypass
    helper.log = []
    with helper.substituted():
        oracle.call(0x530790, instruction_limit=100_000)
        result = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if result != 0:
            raise AssertionError(('installation path initialization', result))
        prefix = bytes(oracle.cpu.mem_read(
            MODEL_PREFIX_TABLE + MODEL_PREFIX_INDEX * MODEL_PREFIX_STRIDE,
            MODEL_PREFIX_STRIDE)).split(b'\0', 1)[0]
    root = str(installation_root).rstrip('\\/')
    expected = root.encode('cp1252') + b'\\Data\\Models\\'
    if prefix != expected:
        raise AssertionError(('model path prefix', prefix, expected))
    return prefix


def _compare_record(oracle, slot, attachment, label, model_prefix):
    cpu = oracle.cpu
    source = oracle.inputs
    target = source + 0x1000
    initial = b'\xa5' * 0x984
    cpu.mem_write(source, slot)
    cpu.mem_write(target, initial)
    oracle.call(0x52c2e0, (target, source, attachment),
                instruction_limit=50_000)
    actual = bytes(cpu.mem_read(target, 0x984))
    expected = transfer_mechanical_physics(slot, attachment,
                                           initial_image=initial)
    expected = transfer_mechanical_presentation(
        slot, model_prefix=model_prefix, initial_image=expected)
    if actual != expected:
        offset = next(index for index, pair in enumerate(zip(actual, expected))
                      if pair[0] != pair[1])
        raise AssertionError((label, hex(offset), actual[offset:offset + 16],
                              expected[offset:offset + 16]))
    if bytes(cpu.mem_read(source, len(slot))) != slot:
        raise AssertionError((label, 'source changed'))


def verify(executable, data_root=None):
    oracle = DynoOracle(executable)
    installation_root = data_root if data_root is not None else r'C:\MCO'
    model_prefix = _initialize_model_prefix(oracle, installation_root)
    comparisons = []
    for case_index, (slot, attachment, label) in enumerate(_cases()):
        _compare_record(oracle, slot, attachment, (case_index, label), model_prefix)
        comparisons.append(label)
    stock_records = 0
    if data_root is not None:
        from client.assets import Assets
        from client.catalogue import Catalogue
        from tools.inspect_stock_mechanical import stock_slots
        assets = Assets(data_root)
        catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
        slots = stock_slots(catalogue, 101, percent_damage=0, item_wear=0)
        expanded = expand_mechanical_parts(slots)
        for part_index, part in enumerate(expanded):
            _compare_record(oracle, slots[part.source_index], part.attachment,
                            ('stock vehicle 101', part_index), model_prefix)
            stock_records += 1
    return {'cases': len(comparisons), 'max_error': 0,
            'original_entry': '0x52c2e0', 'labels': comparisons,
            'stock_records': stock_records,
            'model_prefix': model_prefix.decode('cp1252'),
            'prefix_initializer': '0x530790',
            'scope': 'complete mechanical images; original 0x530790 initializes the path table from shipped pointer/type rows with synthetic registry service and real sprintf; real 0x530a90 lookup, strncpy and sprintf execute for records'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--data-root', type=Path,
                        help='also compare every expanded stock record for vehicle 101')
    args = parser.parse_args()
    print(verify(args.executable, args.data_root))


if __name__ == '__main__':
    main()
