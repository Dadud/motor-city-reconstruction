"""Export synthetic cases by executing all implemented recovery-cell bodies.

Only the hash-checked mcity.exe is admitted by DynoOracle. Inputs are planted
synthetic buffers/globals; outputs are read from original memory/registers,
never computed by the recovered implementation. No PE entry point, imports,
network, original assets or raw executable bytes are used or exported.
"""
import argparse
import json
from pathlib import Path
import struct

from tools.cell_corpus import DEFAULT, write_corpus
from tools.function_cell import load_manifest, manifests

A, B = 0x71001000, 0x71004000
VALUES = (0, 1, 3, 0x12345678, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)


def pattern(size, seed):
    return bytes((seed + index * 37) & 255 for index in range(size))


def line_counter_wrap_probe(oracle):
    """Loop-only evidence; do not count this as a complete-function case."""
    oracle._reset()
    oracle.cpu.mem_write(A, b'AB\n')
    oracle.cpu.mem_write(B, b'\xcc'*8)
    for register, value in ((oracle.reg.UC_X86_REG_EDX, A),
                            (oracle.reg.UC_X86_REG_ECX, B),
                            (oracle.reg.UC_X86_REG_ESI, 0x7fffffff),
                            (oracle.reg.UC_X86_REG_EDI, 0x7fffffff)):
        oracle.cpu.reg_write(register, value)
    oracle._run(0x433e84, 0x433e94, timeout=0, count=100)
    observed = dict(
        scope='0x433e84..0x433e94 loop only; preloaded INT_MAX counter and limit',
        counter_before=0x7fffffff,
        counter_after=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_ESI),
        source_advanced=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EDX)-A,
        destination_advanced=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_ECX)-B,
        copied_bytes=list(oracle.cpu.mem_read(B, 2)))
    if (observed['counter_after'], observed['source_advanced'],
            observed['destination_advanced'], observed['copied_bytes']) != (
            0x80000001, 2, 2, [65, 66]):
        raise AssertionError(('line counter wrap changed', observed))
    return observed


def build(executable):
    from client.dyno import _SOURCE_SHA256
    from tools.native_oracle import DynoOracle
    oracle = DynoOracle(executable)
    oracle.cpu.mem_map(0, 0x1000)
    cells = {}

    def put(address, value):
        oracle.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def word(address):
        return struct.unpack('<I', oracle.cpu.mem_read(address, 4))[0]

    def image(address, size):
        return list(oracle.cpu.mem_read(address, size))

    for path in manifests():
        manifest = load_manifest(path)
        if manifest.get('status') != 'implemented':
            continue
        if manifest['roots'][0]['target_sha256'] != _SOURCE_SHA256:
            raise ValueError(f"{manifest['id']}: unsupported oracle target")
        name = manifest['id']
        entry = int(manifest['roots'][0]['address'], 16)
        cases = []

        def call(args=(), **kwargs):
            oracle.call(entry, args, **kwargs)
            return oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)

        def add(inputs, outputs):
            cases.append(dict(input=list(inputs), output=list(outputs)))

        if name in ('diagnostic_runtime', 'startup_thread_runtime'):
            from importlib import import_module
            cases = import_module('tools.'+name+'_cases').capture(oracle)
        elif name == 'startup_initialize':
            from tools.startup_initialize_cases import capture
            cases = capture(oracle)
        elif name in ('input_mouse_geometry','input_mouse_state_set','input_mouse_callbacks'):
            from importlib import import_module
            cases=import_module('tools.'+name+'_cases').capture(oracle)
        elif name == 'input_mouse_lifetime':
            from tools.input_mouse_lifetime_cases import capture
            cases = capture(oracle)
        elif name == 'input_toggle_key':
            from tools.input_toggle_key_cases import capture
            cases = capture(oracle)
        elif name == 'input_keyboard_layout':
            from tools.input_keyboard_layout_cases import capture
            cases = capture(oracle)
        elif name == 'cleanup_registry':
            from tools.cleanup_registry_cases import capture
            cases = capture(oracle)
        elif name == 'input_console_read':
            from tools.input_console_cases import capture
            cases = capture(oracle)
        elif name == 'input_default_key':
            from tools.input_default_key_cases import capture
            cases = capture(oracle)
        elif name == 'input_callback_dispatch':
            from tools.input_callback_dispatch_cases import capture
            cases = capture(oracle)
        elif name == 'input_device_lifetime':
            from tools.input_device_lifetime_cases import capture
            cases = capture(oracle)
        elif name == 'input_device_information':
            from tools.input_device_information_cases import capture
            cases = capture(oracle)
        elif name == 'input_device_state':
            from tools.input_device_state_cases import capture
            cases = capture(oracle)
        elif name == 'input_device_read':
            from tools.input_device_cases import capture
            cases = capture(oracle)
        elif name in ('input_queue_pop', 'input_queue_peek'):
            from tools.input_consumer_cases import capture
            cases = capture(oracle, name)
        elif name == 'input_scan_translate':
            from tools.input_translation_cases import capture
            cases = capture(oracle)
        elif name in ('input_cursor_warp', 'input_mouse_update', 'input_mouse_press', 'input_mouse_motion'):
            from tools.mouse_input_cases import capture
            cases = capture(oracle, name)
        elif name == 'window_input_initialize':
            from tools.window_initialization_cases import capture
            cases = capture(oracle)
        elif name == 'window_handler_register':
            from tools.window_registration_cases import capture
            cases = capture(oracle)
        elif name == 'window_procedure':
            from tools.window_dispatch_cases import capture
            cases = capture(oracle, True)
        elif name == 'window_message_dispatch':
            from tools.window_dispatch_cases import capture
            cases = capture(oracle)
        elif name == 'free_camera_update':
            from tools.free_camera_cases import capture
            cases = capture(oracle)
        elif name == 'track_surface_lookup':
            from tools.track_surface_cases import capture
            cases = capture(oracle)
        elif name in ('nearest_path_point', 'path_side'):
            from tools.track_path_cases import capture
            cases = capture(oracle, name)
        elif name == 'spatial_grid_lookup':
            from tools.spatial_grid_cases import capture
            cases = capture(oracle)
        elif name == 'camera_matrix_rotation':
            from tools.camera_matrix_rotation_cases import capture
            cases = capture(oracle)
        elif name in ('input_key_down', 'input_key_translate', 'input_queue_resize', 'input_character'):
            from tools.input_queue_cases import capture
            cases = capture(oracle, name, entry)
        elif name in ('input_key_raw', 'input_key_query', 'input_key_release'):
            from tools.input_key_cases import capture
            cases = capture(oracle, name, entry)
        elif name in ('record_selection_cycle', 'record_mode_apply'):
            from tools.camera_cycle_cases import capture
            cases = capture(oracle, name, entry)
        elif name in ('camera_context_special', 'record_selection_apply'):
            from tools.selection_controller_cases import capture
            cases = capture(oracle, name, entry)
        elif name in ('record_handler', 'record_pair_match', 'record_should_retain',
                    'record_machine_initialize', 'record_machine_reset',
                    'record_transition', 'record_activate'):
            from tools.record_machine_cases import capture_cases
            cases = capture_cases(oracle, name, entry)
        elif name == 'record_cursor_pop':
            for cursor in VALUES:
                for base in VALUES:
                    put(0x98c0f8, cursor); put(0x98badc, base)
                    call()
                    add([cursor, base], [word(0x98c0f8)])
        elif name == 'record_stack_contains':
            for seed in (0, 0xa5):
                identifiers = (0, 0x1234, 0x80000000, 0xffffffff,
                               0x1234 if seed else 0x87654321)
                data = bytearray(pattern(1296, seed))
                for index, identifier in enumerate(identifiers):
                    struct.pack_into('<I', data, index*256+4, identifier)
                for cursor in (0, A-1, A, A+255, A+256, A+384,
                               A+768, A+1024, A+1025, A+1279):
                    for target in VALUES + (0x1234, 0x87654321):
                        oracle.cpu.mem_write(A, bytes(data))
                        put(0x98badc, A); put(0x98c0f8, cursor)
                        result = call((target,))
                        add([A, cursor, target, *data], [result, *image(A, 1296)])
        elif name in ('record_identifier', 'record_related_value',
                      'record_signed_negate', 'record_flag_toggle'):
            field = {'record_identifier': 4, 'record_related_value': 0x8c,
                     'record_signed_negate': 0xcc, 'record_flag_toggle': 0x88}[name]
            for seed in (0, 0xa5):
                for value in VALUES:
                    data = bytearray(pattern(272, seed))
                    struct.pack_into('<I', data, field, value)
                    oracle.cpu.mem_write(A, bytes(data)); put(0x98c0f8, A)
                    result = call()
                    outputs = image(A, 272)
                    if name in ('record_identifier', 'record_related_value'):
                        outputs.insert(0, result)
                    add(data, outputs)
        elif name in ('copy_words24', 'record_state_copy48', 'copy_prefix2'):
            length = {'copy_words24': 192, 'record_state_copy48': 512,
                      'copy_prefix2': 96}[name]
            source = 76 if name == 'record_state_copy48' else 32
            deltas = (-24, -16, -8, -4, -1, 0, 1, 4, 8, 16, 20, 24, 64)
            if name == 'copy_prefix2':
                deltas = (-3, -2, -1, 0, 1, 2, 3, 16, 32)
            for seed in (0, 0xa5, 255):
                for delta in deltas:
                    destination = source+delta
                    data = pattern(length, seed)
                    oracle.cpu.mem_write(A, data)
                    if name == 'record_state_copy48':
                        put(0x98c0f8, A+64)
                        flags = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EFLAGS)
                        oracle.cpu.reg_write(oracle.reg.UC_X86_REG_EFLAGS, flags & ~0x400)
                        call((0xdeadbeef, A+destination))
                        inputs = [64, destination, *data]
                    elif name == 'copy_words24':
                        result = call((A+source,), this_pointer=A+destination, cleanup=b'')
                        inputs = [source, destination, *data]
                    else:
                        call((A+destination, A+source))
                        inputs = [source, destination, *data]
                    outputs = image(A, length)
                    if name == 'copy_words24':
                        outputs.insert(0, (result-A) & 0xffffffff)
                    add(inputs, outputs)
        elif name == 'copy_line_segment':
            payloads = (b'\nabc', b'ab\ncd', b'a\0b\nc', b'abc\r\nq',
                        bytes(range(32)), b'x'*32)
            for payload in payloads:
                for delta in (-16, -4, -1, 0, 1, 4, 16, 64):
                    for limit in (0x80000000, 0xffffffff, 0, 1, 2, 7, 12):
                        source, destination = 64, 64+delta
                        data = bytearray(pattern(192, delta))
                        data[source:source+32] = (payload+b'Z'*32)[:32]
                        oracle.cpu.mem_write(A, bytes(data))
                        result = call((A+destination, A+source, limit))
                        add([source, destination, limit, *data],
                            [(result-(A+source)) & 0xffffffff, *image(A, 192)])
            for payload in (b'\n', b'abc\n'):
                data = bytearray(pattern(192, 0xa5))
                data[64:96] = (payload+b'Z'*32)[:32]
                oracle.cpu.mem_write(A, bytes(data))
                result = call((A+128, A+64, 0x7fffffff))
                add([64, 128, 0x7fffffff, *data],
                    [(result-(A+64)) & 0xffffffff, *image(A, 192)])
        elif name in ('entity_side_flag', 'entity_mode_flag', 'entity_word_assign',
                    'entity_byte_assign', 'entity_side_flag_assign'):
            # Scalar inputs retain their original bits; byte arguments are
            # narrowed only where the machine code reads a byte on the stack.
            sides = (0, 1, 0x80000000, 0x100)
            indexes = (0, 1, 7, 8, 17, 0x7fffffff)
            if name.endswith('_flag'):
                for flags in (0, 1, 2, 4, 8, 0x10, 0x20, 0xff):
                    for side in sides:
                        for index in (0, 1, 7):
                            data = bytearray(pattern(256, flags+side))
                            data[index*28+26] = flags
                            oracle.cpu.mem_write(A, bytes(data)); put(0x8e3ab8, A)
                            args = (index, 0xaabbccdd, side) if name == 'entity_side_flag' else (side, index)
                            result = call(args) & 255
                            add([1, index, side, *data], [result, *image(A, 256)])
                for side in sides:
                    data = pattern(256, 0xa5)
                    oracle.cpu.mem_write(A, data); put(0x8e3ab8, 0)
                    args = (0xffffffff, 0, side) if name == 'entity_side_flag' else (side, 0xffffffff)
                    result = call(args) & 255
                    add([0, 0xffffffff, side, *data], [result, *image(A, 256)])
            else:
                values = ((0, 0x80000000, 0x3f800000, 0xbf800000, 1, 0x80000001,
                           0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000)
                          if name == 'entity_word_assign' else
                          (0, 1, 2, 0x10, 0x20, 0xff, 0x100, 0x101, 0x80000000, 0xffffffff))
                for k, value in enumerate(values):
                    for side in sides:
                        for index in indexes:
                            count = (1, 3, 8)[(k+side+index) % 3]
                            data = pattern(256, k*13+side)
                            oracle.cpu.mem_write(A, data); put(0x8e3ab8, A)
                            put(0x988e38, count)
                            call((index, 0xaabbccdd, side, value))
                            add([1, index, count, side, value, *data], image(A, 256))
                # Signed IDIV remainder zero is valid even for negative indices.
                for index in (0xffffffff, 0x80000000):
                    data = pattern(256, index)
                    oracle.cpu.mem_write(A, data); put(0x8e3ab8, A); put(0x988e38, 1)
                    call((index, 0, 1, 1))
                    add([1, index, 1, 1, 1, *data], image(A, 256))
                for index in (0, 0xffffffff):
                    data = pattern(256, 0xa5)
                    oracle.cpu.mem_write(A, data); put(0x8e3ab8, 0); put(0x988e38, 0)
                    call((index, 0, 1, 0xffffffff))
                    add([0, index, 0, 1, 0xffffffff, *data], image(A, 256))
        elif name == 'cyclic_index_difference':
            for first in VALUES:
                for second in VALUES:
                    for count in (0, 1, 3, 12, 0x7fffffff, 0x80000000, 0xffffffff):
                        for mode in (0, 1, 0x80000000):
                            put(0x988e38, count); put(0x9aaa74, mode)
                            add([first, second, count, mode], [call((first, second))])
        elif name in ('clamped_bit_mask', 'indexed_masked_bit'):
            indexes = (0x80000000, 0xfffffffe, 0xffffffff, 0, 1, 13, 14,
                       15, 16, 0x7ffffffe, 0x7fffffff)
            if name == 'clamped_bit_mask':
                for index in indexes:
                    add([index], [call((index,))])
            else:
                for record in (0, 1, 3):
                    for mask in (0, 0xffff, 0x8001, 0xffffffff, 0x12345678):
                        for index in indexes:
                            data = bytearray(pattern(352, mask))
                            struct.pack_into('<I', data, record*84+76, mask)
                            oracle.cpu.mem_write(A, bytes(data)); put(0x97c38c, A)
                            result = call((record, index))
                            add([record, index, *data], [result, *image(A, 352)])
        elif name in ('instance_accessor', 'singleton_quotient'):
            if name == 'instance_accessor':
                for primary in VALUES:
                    for fallback in VALUES:
                        put(0x9aaa98, primary); put(0x988e38, fallback)
                        add([primary, fallback], [call()])
            else:
                from tools.w0_int_leaf_oracle import QUOTIENT_CASES
                for primary, dividend, fallback in QUOTIENT_CASES:
                    put(0x9aaa98, primary); put(0x988e38, fallback)
                    result = call((dividend,))
                    add([dividend & 0xffffffff, primary & 0xffffffff,
                         fallback & 0xffffffff], [result])
        elif name == 'global_store':
            for stored in VALUES:
                for returned in VALUES:
                    initial = pattern(4, 0xcc)
                    oracle.cpu.mem_write(A, initial)
                    put(0x8e3ac0, stored); put(0x8e3abc, returned)
                    result = call((A,))
                    add([stored, returned, *initial], [result, *image(A, 4)])
        elif name in ('state_and_flag', 'state_clear_mask', 'state_or_mask'):
            for state in VALUES:
                for mask in VALUES:
                    put(A+0x6c, state)
                    result = call((mask,), this_pointer=A, cleanup=b'')
                    add([state, mask], [result if name == 'state_and_flag'
                                       else word(A+0x6c)])
        elif name in ('counter_increment', 'counter_mod4', 'zero_flag'):
            address = dict(counter_increment=0x92beb0, counter_mod4=0x9aba2c,
                           zero_flag=0x929888)[name]
            for value in VALUES + (2, 4, 5):
                put(address, value)
                result = call()
                add([value], [result if name == 'counter_increment' else word(address)])
        elif name == 'sentinel_match':
            for value in VALUES + (0xfeeeeb19, 0xfeeeeb18, 0xfeeeeb1a):
                add([value], [call((value,))])
        elif name == 'default_constants':
            call()
            add([], struct.unpack('<III', oracle.cpu.mem_read(0x88aafc, 12)))
        elif name in ('table_read_a', 'table_read_b', 'table_byte_read',
                      'table_byte_read_xy', 'entity_flag', 'entity_flag3'):
            size = 900 if name == 'table_byte_read_xy' else 256
            base = dict(table_read_a=0x92c24c, table_read_b=0x98bae0,
                        table_byte_read=0x97ebcc, table_byte_read_xy=0x97e848,
                        entity_flag=A, entity_flag3=A)[name]
            # Distinct seeds prevent constant-zero table contents from hiding errors.
            for seed in (0, 0xa5):
                data = pattern(size, seed)
                oracle.cpu.mem_write(base, data)
                if name.startswith('entity_flag'):
                    put(0x8e3ab8, base)
                    indexes = (0, 1, 3, 7)
                elif name.startswith('table_read'):
                    indexes = (0, 1, 3, 7)
                else:
                    indexes = (0, 1, 127, 255, 0xffffffff)
                for index in indexes:
                    if name == 'table_byte_read_xy':
                        for row in (0, 1, 2):
                            result = call((row, index)) & 255
                            add([row, index, *data], [result])
                    else:
                        result = call((index,))
                        if name == 'table_byte_read':
                            result &= 255
                        add([index, *data], [result])
            if name == 'entity_flag3':
                put(0x8e3ab8, 0)
                add([0, *bytes(256)], [call((0,))])
                # Explicit empty-span marker; the regular cases use the same
                # fixed-sized transport but a separate presence word.
                cases[-1]['input'].insert(0, 0)
                for case in cases[:-1]:
                    case['input'].insert(0, 1)
        elif name in ('buffer_copy12_a', 'buffer_copy12_b'):
            for seed in (0, 17, 255):
                destination, source = pattern(24, seed), pattern(12, seed+71)
                oracle.cpu.mem_write(A, destination)
                oracle.cpu.mem_write(B, source)
                call((B,), this_pointer=A, cleanup=b'')
                add([*destination, *source], image(A, 24) + image(B, 12))
        elif name in ('entity_clear', 'entity_or_store'):
            size = 0x124 if name == 'entity_clear' else 0x9c
            for value in VALUES:
                data = pattern(size, value & 255)
                oracle.cpu.mem_write(A, data)
                if name == 'entity_clear':
                    call(this_pointer=A)
                    add(data, image(A, size))
                else:
                    call((value,), this_pointer=A, cleanup=b'')
                    add([value, *data], image(A, size))
        elif name == 'struct_initializer':
            for seed in (0, 17, 255):
                first, second = pattern(8, seed), pattern(16, seed+37)
                oracle.cpu.mem_write(A, first); oracle.cpu.mem_write(B, second)
                call((A, B))
                add([*first, *second], image(A, 8) + image(B, 16))
        elif name == 'registry_register':
            for counter in VALUES:
                for head in (0, B, 0xffffffff):
                    data = pattern(0x5c, 0xab)
                    oracle.cpu.mem_write(A, data)
                    put(0x886b9c, counter); put(0x8e3b30, head)
                    call((A,))
                    add([counter, head, *data], [word(0x886b9c), *image(A, 0x5c)])
                    if word(0x8e3b30) != A:
                        raise AssertionError('original registry head was not updated')
        elif name in ('registry_reset', 'registry_slot_write', 'registry_slot_used'):
            for seed in (0, 0xaa):
                for slot in ((0,) if name == 'registry_reset' else (0, 1, 7, 255)):
                    data = bytearray(pattern(0x1804, seed))
                    if name == 'registry_slot_used' and seed == 0:
                        data[slot*24:slot*24+4] = bytes(4)
                    oracle.cpu.mem_write(0x8e3b38, bytes(data))
                    if name == 'registry_reset':
                        call(); add(data, image(0x8e3b38, len(data)))
                    elif name == 'registry_slot_write':
                        values = (0x12345678, 0x80000000, 0xffffffff)
                        call((slot, *values))
                        add([slot, *values, *data], image(0x8e3b38, len(data)))
                    else:
                        result = call((slot,))
                        add([slot, *data], [result])
        elif name in ('primary_value_store', 'counter_assign'):
            address = 0x92970c if name == 'primary_value_store' else 0x9aba2c
            for value in VALUES + (2, 4, 5):
                initial = value ^ 0xffffffff
                put(address, initial)
                call((value,))
                add([initial, value], [word(address)])
        elif name == 'buffer_set_length':
            for seed in (0, 17, 255):
                for length in (0, 1, 7, 15):
                    data = pattern(20, seed)
                    owner = pattern(16, seed+71)
                    oracle.cpu.mem_write(A, owner)
                    put(A+4, B)
                    oracle.cpu.mem_write(B, data)
                    call((length,), this_pointer=A, cleanup=b'')
                    add([struct.unpack('<I', owner[8:12])[0], length, *data],
                        [word(A+8), *image(B, len(data))])
                    if image(A, 4) != list(owner[:4]) or image(A+12, 4) != list(owner[12:]):
                        raise AssertionError('length setter changed unrelated owner fields')
                    if word(A+4) != B:
                        raise AssertionError('length setter changed buffer pointer')
        elif name == 'selection_state_normalize':
            import random
            rng = random.Random(0x4325c0)
            edges = (0, 1, 3, 4, 5, 6, 0x7fffffff, 0x80000000,
                     0xfffffffa, 0xfffffffb, 0xfffffffc, 0xffffffff)
            rows = [[value]*6 for value in edges]
            rows += [[edges[(k+j) % len(edges)] for j in range(6)]
                     for k in range(len(edges))]
            rows += [[rng.getrandbits(32) for _ in range(6)] for _ in range(512)]
            for values in rows:
                data = struct.pack('<6I', *values)
                oracle.cpu.mem_write(A, data)
                result = call(this_pointer=A)
                add(list(data), [result, *image(A, 24)])
        elif name == 'table_slot_clear':
            for seed in (0, 0xa5):
                for polarity in (0, 1):
                    present = [(k + polarity) % 2 for k in range(256)]
                    for slot in (0, 1, 7, 255):
                        data = pattern(256*12, seed)
                        oracle.cpu.mem_write(A, data)
                        for index, enabled in enumerate(present):
                            put(0x92c40c + index*4, A + index*12 if enabled else 0)
                        call((slot,))
                        add([slot, *present, *data], image(A, len(data)))
        elif name in ('scratch_clear_return', 'pointer_clear_record',
                      'pointer_clear_record_b', 'pointer_clear_record_c'):
            for present in (0, 1):
                for value in VALUES:
                    initial = pattern(8, 0xcc)
                    oracle.cpu.mem_write(A, initial)
                    if name == 'scratch_clear_return':
                        put(0x92971c, value); put(0x929720, A if present else 0)
                        result = call()
                        add([present, value, *initial], [result, *image(A, 8)])
                    else:
                        pointer_global, record_global = {
                            'pointer_clear_record': (0x988d08, 0x988cf4),
                            'pointer_clear_record_b': (0x988d0c, 0x988cfc),
                            'pointer_clear_record_c': (0x988d10, 0x988d04)}[name]
                        put(pointer_global, A if present else 0); put(record_global, value)
                        call()
                        add([A if present else 0, value, *initial],
                            [word(record_global), *image(A, 8)])
        else:
            raise ValueError(f'{name}: no original-execution adapter')
        cells[name] = dict(address=manifest['roots'][0]['address'], cases=cases)
    from tools.record_machine_cases import lifecycle_cases, HANDLERS
    from tools.selection_controller_cases import lifecycle_cases as selection_lifecycle_cases
    from tools.camera_cycle_cases import lifecycle_cases as cycle_lifecycle_cases
    from tools.input_key_cases import lifecycle_cases as key_lifecycle_cases
    from tools.input_queue_cases import lifecycle_cases as queue_lifecycle_cases
    from tools.input_device_information_cases import lifecycle_cases as information_lifecycle_cases
    from tools.input_device_lifetime_cases import lifecycle_cases as device_lifetime_cases
    from tools.input_device_session_cases import lifecycle_cases as device_session_cases
    from tools.input_callback_dispatch_cases import lifecycle_cases as dispatch_lifecycle_cases
    from tools.input_default_key_cases import lifecycle_cases as default_key_lifecycle_cases
    from tools.input_action_session_cases import lifecycle_cases as action_session_cases
    from tools.startup_initialize_cases import lifecycle_cases as startup_lifecycle_cases
    from tools.startup_toggle_cases import lifecycle_cases as startup_toggle_lifecycle_cases
    from tools.combined_input_cases import lifecycle_cases as combined_input_lifecycle_cases
    from tools.startup_mouse_cases import lifecycle_cases as startup_mouse_lifecycle_cases
    from tools.input_mouse_runtime_cases import lifecycle_cases as mouse_runtime_lifecycle_cases
    from tools.input_keyboard_layout_cases import lifecycle_cases as keyboard_layout_lifecycle_cases
    from tools.cleanup_registry_cases import lifecycle_cases as cleanup_registry_lifecycle_cases
    from tools.input_console_cases import lifecycle_cases as console_lifecycle_cases
    from tools.free_camera_cases import lifecycle_cases as camera_lifecycle_cases
    from tools.mouse_input_cases import lifecycle_cases as mouse_lifecycle_cases
    return dict(schema=1, target_sha256=manifest['roots'][0]['target_sha256'],
                provenance='tools.w0_cell_corpus; hash-checked Unicorn x86 execution; '
                           'synthetic inputs; cells execute complete bodies on bounded '
                           'domains; separate probes label loop-only and connected-call scopes',
                substitutions={'record_callbacks': dict(
                    handler_ids=list(HANDLERS),
                    behavior='RET plus declared observation/mutation hooks; controller bodies unchanged')},
                probes={'combined_input_lifecycle': combined_input_lifecycle_cases(oracle),
                        'line_counter_wrap': line_counter_wrap_probe(oracle),
                        'record_lifecycle': lifecycle_cases(oracle),
                        'record_selection_lifecycle': selection_lifecycle_cases(oracle),
                        'record_cycle_lifecycle': cycle_lifecycle_cases(oracle),
                        'input_key_lifecycle': key_lifecycle_cases(oracle),
                        'input_queue_lifecycle': queue_lifecycle_cases(oracle),
                        'input_device_information_lifecycle': information_lifecycle_cases(oracle),
                        'input_device_lifetime_lifecycle': device_lifetime_cases(oracle),
                        'input_device_session': device_session_cases(oracle),
                        'input_callback_dispatch_lifecycle': dispatch_lifecycle_cases(oracle),
                        'input_default_key_lifecycle': default_key_lifecycle_cases(oracle),
                        'input_action_session': action_session_cases(oracle),
                        'input_console_lifecycle': console_lifecycle_cases(oracle),
                        'cleanup_registry_lifecycle': cleanup_registry_lifecycle_cases(oracle),
                        'input_keyboard_layout_lifecycle': keyboard_layout_lifecycle_cases(oracle),
                        'startup_lifecycle': startup_lifecycle_cases(oracle),
                        'startup_toggle_lifecycle': startup_toggle_lifecycle_cases(oracle),
                        'startup_mouse_lifecycle': startup_mouse_lifecycle_cases(oracle),
                        'input_mouse_runtime_lifecycle': mouse_runtime_lifecycle_cases(oracle),
                        'free_camera_lifecycle': camera_lifecycle_cases(oracle),
                        'window_camera_lifecycle': camera_lifecycle_cases(oracle, True),
                        'window_mouse_lifecycle': mouse_lifecycle_cases(oracle)},
                cells=cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    corpus = build(args.executable)
    write_corpus(args.output, corpus)
    print(json.dumps(dict(output=str(args.output), cells=len(corpus['cells']),
                          cases=sum(len(c['cases']) for c in corpus['cells'].values()))))


if __name__ == '__main__':
    main()
