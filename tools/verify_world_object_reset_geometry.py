"""Compare 0x53d640 with translated wheel/drive reset child behavior."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_reset import (OWNER_SIZE, WheelResetCache,
                                       reset_wheel_records,
                                       reset_world_object_drive_state,
                                       reset_world_object_geometry)
from tools.native_oracle import DynoOracle

OWNER = 0x72002000
CHILDREN = {0x0053D4A0, 0x00549660}
PROFILE = 0x71005000
INIT_FLAG = 0x00A55700
FACTOR = 0x00A55704


def verify(executable, cases=96):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x53D640)
    for case in range(cases):
        initial = bytearray(rng.randbytes(OWNER_SIZE))
        profile = bytearray(rng.randbytes(0x690))
        profile_mode = case & 1
        struct.pack_into('<I', initial, 0x1c94, PROFILE)
        struct.pack_into('<f', initial, 0x18ec, rng.uniform(1, 100))
        struct.pack_into('<f', initial, 0x18f0, rng.uniform(1, 100))
        struct.pack_into('<i', initial, 0xac0, rng.choice((-12, -3, 1, 7, 24)))
        struct.pack_into('<f', initial, 0x1898, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0x1894, rng.uniform(-500, 500))
        struct.pack_into('<f', initial, 0xad4, rng.uniform(0.0, 1.5))
        struct.pack_into('<f', initial, 0xadc, rng.uniform(-2, 30))
        struct.pack_into('<f', initial, 0xacc, rng.uniform(-2, 30))
        struct.pack_into('<I', profile, 0x68c, profile_mode)
        struct.pack_into('<f', profile, 0x374, rng.uniform(0.1, 5.0))
        struct.pack_into('<I', profile, 0x6c, rng.randrange(0, 5000))
        cache = WheelResetCache(bool(case & 2), rng.uniform(0.1, 5.0))
        reset_status = (case >> 2) & 1
        cpu.mem_write(PROFILE, bytes(profile))
        cpu.mem_write(INIT_FLAG, struct.pack('<I', int(cache.initialized)))
        cpu.mem_write(FACTOR, struct.pack('<f', cache.factor))
        cpu.mem_write(OWNER, bytes(initial))

        def isolate_reset_children(machine, address, _size, _data):
            if address not in CHILDREN:
                return
            image = bytearray(machine.mem_read(OWNER, OWNER_SIZE))
            active_cache = WheelResetCache(
                bool(struct.unpack('<I', machine.mem_read(INIT_FLAG, 4))[0] & 1),
                struct.unpack('<f', machine.mem_read(FACTOR, 4))[0])
            if address == 0x0053D4A0:
                reset_wheel_records(image, cache=active_cache,
                                    profile_scale=struct.unpack_from('<f', profile, 0x374)[0])
                machine.mem_write(INIT_FLAG, struct.pack('<I', int(active_cache.initialized)))
                machine.mem_write(FACTOR, struct.pack('<f', active_cache.factor))
            else:
                reset_world_object_drive_state(image, profile,
                    reset_drive_state=lambda _: reset_status,
                    interface_result=0)
            machine.mem_write(OWNER, bytes(image))
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

        hook = cpu.hook_add(UC_HOOK_CODE, isolate_reset_children)
        try:
            oracle.call(0x0053D640, (OWNER,), instruction_limit=100000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, OWNER_SIZE))
        original_globals = bytes(cpu.mem_read(INIT_FLAG, 8))
        translated = bytearray(initial)
        expected_cache = WheelResetCache(cache.initialized, cache.factor)
        reset_world_object_geometry(translated,
            reset_component=lambda owner: reset_wheel_records(
                owner, cache=expected_cache,
                profile_scale=struct.unpack_from('<f', profile, 0x374)[0]),
            update_attachment=lambda owner: reset_world_object_drive_state(
                owner, profile, reset_drive_state=lambda _: reset_status,
                interface_result=0))
        if original != translated:
            differences = [i for i, (left, right) in enumerate(zip(original, translated))
                           if left != right]
            raise AssertionError(f'0x53d640 mismatch in case {case}; '
                                 f'bytes {[hex(i) for i in differences[:24]]}; '
                                 f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:10]]}; '
                                 f'python={[(hex(i), translated[i:i+4].hex()) for i in differences[:10]]}')
        expected_globals = struct.pack('<If', int(expected_cache.initialized),
                                       expected_cache.factor)
        if original_globals != expected_globals:
            raise AssertionError(f'0x53d640 child-global mismatch in case {case}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=96)
    args = parser.parse_args()
    count = verify(args.executable, args.cases)
    print(f'0x53d640 and translated reset-child effects match {count} original '
          'owner records; the 0x549660 virtual result is controlled as zero')


if __name__ == '__main__':
    main()
