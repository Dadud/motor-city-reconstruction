"""Compare 0x43ba40's path/offset search orchestration with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.collision_recovery import search_surface_correction
from client.track_topology import track_index_is_rejected
from tools.native_oracle import DynoOracle


def verify(executable, cases=128):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = 0x72002000
    interface, vtable, entry = 0x71001000, 0x71001100, 0x71002000
    table = 0x71003000
    fallback_table = 0x71004000
    cpu.mem_write(0x00A65BD0, struct.pack('<I', interface))
    cpu.mem_write(interface, struct.pack('<I', vtable))
    cpu.mem_write(vtable + 0x10, struct.pack('<I', entry))
    cpu.mem_write(0x0097C38C, struct.pack('<I', table))
    cpu.mem_write(0x008E3AB8, struct.pack('<I', fallback_table))

    rng = random.Random(0x43BA40)
    for case in range(cases):
        path_count = rng.randint(2, 8)
        attempts = path_count
        query_index = rng.randrange(path_count)
        initial_index = rng.randrange(path_count)
        special = bool(rng.getrandbits(1))
        alternate_side = bool(rng.getrandbits(1))
        response_mode = bool(rng.getrandbits(1))
        wrapped_ordering = bool(rng.getrandbits(1))
        wrapped_index = bool(rng.getrandbits(1))
        hit_after = rng.choice((None, 1, 2, 4, 8, 16, 32))

        rows = []
        fallback_rows = bytearray(path_count * 0x1c)
        for index in range(path_count):
            negative = struct.unpack('<f', struct.pack('<f', rng.uniform(1.0, 8.0)))[0]
            positive = struct.unpack('<f', struct.pack('<f', rng.uniform(1.0, 8.0)))[0]
            negative_count = rng.randint(0, 4)
            positive_count = rng.randint(0, 4)
            rows.append((negative, positive, negative_count, positive_count))
            address = table + index * 0x54
            cpu.mem_write(address + 0x38, struct.pack('<2f', negative, positive))
            cpu.mem_write(address + 0x44,
                          struct.pack('<2I', negative_count, positive_count))
            struct.pack_into('<2f', fallback_rows, index * 0x1c + 0x10,
                             rng.uniform(-12.0, 12.0),
                             rng.uniform(-12.0, 12.0))
        cpu.mem_write(fallback_table, bytes(fallback_rows))

        record = bytearray(0xDF8)
        struct.pack_into('<I', record, 0x370, query_index)
        struct.pack_into('<I', record, 0xDF4, 0x800 if response_mode else 0)
        struct.pack_into('<I', record, 0x464, int(alternate_side))
        cpu.mem_write(owner, bytes(record))
        cpu.mem_write(0x00988E38, struct.pack('<I', attempts))
        cpu.mem_write(0x009AAA74, struct.pack('<I', int(not wrapped_ordering)))
        cpu.mem_write(0x009AAA78, struct.pack('<I', 1 if wrapped_index else 0))
        cpu.mem_write(0x009AAA7C, struct.pack('<I', 1))
        cpu.mem_write(0x009AAA90, struct.pack('<i', 0))
        cpu.mem_write(0x009AAA94, struct.pack('<i', 0))
        special_code = b'\xb8' + struct.pack('<I', int(special)) + b'\xc2\x08\x00'
        cpu.mem_write(entry, special_code)
        actual_probes = []
        actual_responses = []
        actual_topology = []
        probe_count = 0

        def intercept(machine, address, _size, _data):
            nonlocal probe_count
            if address in (0x00406840, 0x004066F0):
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                actual_topology.append((address, struct.unpack(
                    '<3I', machine.mem_read(stack, 12)),
                    struct.unpack('<I', machine.mem_read(0x009AAA74, 4))[0],
                    struct.unpack('<II', machine.mem_read(0x009AAA78, 8))))
            if address == 0x0043BD30:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                ret, obj, index, offset, fourth, fifth = struct.unpack(
                    '<6I', machine.mem_read(stack, 24))
                actual_probes.append((obj, index,
                                      struct.unpack('<f', struct.pack('<I', offset))[0],
                                      fourth, fifth))
                probe_count += 1
                machine.reg_write(reg.UC_X86_REG_EAX,
                                  int(hit_after is not None and probe_count == hit_after))
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)
            elif address == 0x0051E460:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                ret, obj, index, offset, mode = struct.unpack(
                    '<5I', machine.mem_read(stack, 20))
                offset = struct.unpack('<f', machine.mem_read(offset, 4))[0]
                actual_responses.append((obj, index,
                                         offset, mode))
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            try:
                oracle.call(0x0043BA40, (owner, initial_index),
                            instruction_limit=500000)
            except Exception as error:
                eip = cpu.reg_read(reg.UC_X86_REG_EIP)
                raise RuntimeError(f'0x43ba40 oracle fault case={case} EIP={eip:#x}') from error
        finally:
            cpu.hook_del(hook)

        expected_probes = []
        expected_responses = []
        translated = bytearray(record)

        def probe(obj, index, offset, fourth, fifth):
            expected_probes.append((owner, index, offset, fourth, fifth))
            return hit_after is not None and len(expected_probes) == hit_after

        def response(obj, index, offset, mode):
            expected_responses.append((owner, index, offset, mode))

        search_surface_correction(
            translated, initial_index, path_rows=rows, path_count=path_count,
            attempts=attempts, wrapped_ordering=wrapped_ordering,
            wrapped_index=wrapped_index, probe=probe, apply_response=response,
            fallback_table=fallback_rows, special_probe=special,
            alternate_track_side=alternate_side, response_mode=response_mode,
            index_is_rejected=lambda index: track_index_is_rejected(
                index, range_start=0, range_end=1,
                lower_limit=0, upper_limit=0))

        native_counter = bytes(cpu.mem_read(owner + 0x5b4, 4))
        translated_counter = bytes(translated[0x5b4:0x5b8])
        if native_counter != translated_counter:
            raise AssertionError(
                f'0x43ba40 probe-generation counter mismatch case={case}: '
                f'native={native_counter.hex()} translated={translated_counter.hex()}')
        if actual_probes != expected_probes or actual_responses != expected_responses:
            raise AssertionError(
                f'0x43ba40 orchestration mismatch case {case}: '
                f'config={(path_count, attempts, query_index, initial_index, special, alternate_side, response_mode, wrapped_ordering, wrapped_index, hit_after)}; '
                f'row={rows[initial_index]}; '
                f'topology calls={actual_topology}; '
                f'actual probes={actual_probes}; expected={expected_probes}; '
                f'actual responses={actual_responses}; expected={expected_responses}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(f'0x43ba40 path/offset search order matches the original for '
          f'{verify(args.executable, args.cases)} cases with geometric and '
          'state-update children intercepted')


if __name__ == '__main__':
    main()
