"""Compare the reset prefix of 0x43b750 through child 0x53d640."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_reset import (OWNER_SIZE, prepare_world_object_reset,
                                       WheelResetCache,
                                       reset_world_object_drive_state,
                                       reset_world_object_geometry,
                                       reset_world_object_prefix,
                                       reset_wheel_records)
from tools.native_oracle import DynoOracle


OWNER = 0x72002000
STOP_BEFORE_CHILD = 0x0053D640
PROFILE = 0x71005000
INIT_FLAG = 0x00A55700
FACTOR = 0x00A55704


def verify(executable, cases=96):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43B750)
    maximum_differences = 0
    for case in range(cases):
        initial = bytearray(rng.randbytes(OWNER_SIZE))
        shared = rng.getrandbits(32)
        profile_scale = rng.uniform(0.1, 20.0)
        profile = bytearray(rng.randbytes(0x690))
        struct.pack_into('<f', profile, 0x20, profile_scale)
        struct.pack_into('<f', profile, 0x374, rng.uniform(0.1, 5.0))
        struct.pack_into('<I', profile, 0x68c, case & 1)
        struct.pack_into('<I', profile, 0x6c, rng.randrange(0, 5000))
        cache = WheelResetCache(bool(case & 1), rng.uniform(0.1, 5.0))
        struct.pack_into('<I', initial, 0x1c94, PROFILE)
        struct.pack_into('<f', initial, 0x18ec, rng.uniform(1, 100))
        struct.pack_into('<f', initial, 0x18f0, rng.uniform(1, 100))
        struct.pack_into('<i', initial, 0xac0, rng.choice((-12, -3, 1, 7, 24)))
        struct.pack_into('<f', initial, 0x1898, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0x1894, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0xad4, rng.uniform(0.0, 1.5))
        struct.pack_into('<f', initial, 0xadc, rng.uniform(-2, 30))
        struct.pack_into('<f', initial, 0xacc, rng.uniform(-2, 30))
        cpu.mem_write(PROFILE, bytes(profile))
        cpu.mem_write(OWNER, bytes(initial))
        cpu.mem_write(0x0098C468, struct.pack('<I', shared))
        stopped = []

        def stop_before_reset_child(machine, address, _size, _data):
            if address == STOP_BEFORE_CHILD:
                stopped.append(True)
                machine.reg_write(reg.UC_X86_REG_EIP, oracle.stop)

        hook = cpu.hook_add(UC_HOOK_CODE, stop_before_reset_child)
        try:
            oracle.call(0x0043B750, (OWNER,), instruction_limit=200000)
        finally:
            cpu.hook_del(hook)
        if not stopped:
            raise AssertionError(f'case {case} did not reach reset child boundary')
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        translated = bytearray(initial)
        reset_world_object_prefix(translated, shared)
        if original != translated:
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            maximum_differences = max(maximum_differences, len(differences))
            raise AssertionError(f'0x43b750 reset-prefix mismatch in case {case}; '
                                 f'bytes {[hex(i) for i in differences[:20]]}; '
                                 f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:8]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:8]]}')

        # Continue the original outer reset through translated child 0x53d640
        # and stop at its next child boundary, 0x43f090.
        cpu.mem_write(OWNER, bytes(initial))
        cpu.mem_write(0x0098C468, struct.pack('<I', shared))
        cpu.mem_write(INIT_FLAG, struct.pack('<I', int(cache.initialized)))
        cpu.mem_write(FACTOR, struct.pack('<f', cache.factor))
        reached_geometry = []
        reached_next_child = []

        def translate_geometry_child(machine, address, _size, _data):
            if address == 0x0053D640:
                reached_geometry.append(True)
                image = bytearray(machine.mem_read(OWNER, OWNER_SIZE))
                active_cache = WheelResetCache(
                    bool(struct.unpack('<I', machine.mem_read(INIT_FLAG, 4))[0] & 1),
                    struct.unpack('<f', machine.mem_read(FACTOR, 4))[0])
                reset_world_object_geometry(image,
                    reset_component=lambda owner: reset_wheel_records(
                        owner, cache=active_cache, profile_scale=profile_scale),
                    update_attachment=lambda owner: reset_world_object_drive_state(
                        owner, profile, reset_drive_state=lambda _: (case >> 1) & 1,
                        interface_result=0))
                machine.mem_write(OWNER, bytes(image))
                machine.mem_write(INIT_FLAG, struct.pack('<I', int(active_cache.initialized)))
                machine.mem_write(FACTOR, struct.pack('<f', active_cache.factor))
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, return_address)
            elif address == 0x0043F090:
                reached_next_child.append(True)
                machine.reg_write(reg.UC_X86_REG_EIP, oracle.stop)

        hook = cpu.hook_add(UC_HOOK_CODE, translate_geometry_child)
        try:
            oracle.call(0x0043B750, (OWNER,), instruction_limit=300000)
        finally:
            cpu.hook_del(hook)
        if not reached_geometry or not reached_next_child:
            raise AssertionError(f'case {case} missed a reset pipeline boundary')
        original_pipeline = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        translated_pipeline = bytearray(initial)
        prepare_world_object_reset(translated_pipeline, shared,
            reset_component=lambda owner: reset_wheel_records(
                owner, cache=cache, profile_scale=profile_scale),
            update_attachment=lambda owner: reset_world_object_drive_state(
                owner, profile, reset_drive_state=lambda _: (case >> 1) & 1,
                interface_result=0))
        if original_pipeline != translated_pipeline:
            differences = [i for i, (left, right) in enumerate(
                zip(original_pipeline, translated_pipeline)) if left != right]
            raise AssertionError(f'0x43b750/0x53d640 composed mismatch in case {case}; '
                                 f'bytes {[hex(i) for i in differences[:20]]}')
        expected_globals = struct.pack('<If', int(cache.initialized), cache.factor)
        if bytes(cpu.mem_read(INIT_FLAG, 8)) != expected_globals:
            raise AssertionError(f'composed reset global cache mismatch in case {case}')
    return cases, maximum_differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    cases, differences = verify(args.executable, args.cases)
    print(f'0x43b750 reset prefix matches {cases} original owner records at '
          f'0x53d640; composed 0x43b750/0x53d640 matches through 0x43f090; '
          f'maximum differing bytes {differences}')


if __name__ == '__main__':
    main()
