"""Compare default driver-node insertion `0x52c190` against original memory."""
import argparse
import struct

from client.model_owner import build_default_driver_node
from tools.native_oracle import DynoOracle


OWNER_SIZE = 0x878
NODE_SIZE = 0x984


def verify(executable):
    import unicorn

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    base = 0x74000000
    cpu.mem_map(base, 0x40000)
    owner = base + 0x1000
    node = base + 0x10000
    allocation_fails = False
    allocations, lookups = [], []
    lookup_value = 0x730080E9

    def intercept(uc, address, _size, _user):
        nonlocal allocation_fails
        if address not in (0x6ee530, 0x528a70):
            return
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        ret, = struct.unpack('<I', uc.mem_read(esp, 4))
        if address == 0x6ee530:
            _, tag_ptr, size, pool = struct.unpack('<IIII', uc.mem_read(esp, 16))
            tag = bytes(uc.mem_read(tag_ptr, 32)).split(b'\0', 1)[0]
            allocations.append((tag, size, pool))
            result = 0 if allocation_fails else node
            uc.reg_write(reg.UC_X86_REG_EAX, result)
        else:
            kind, attachment = struct.unpack('<II', uc.mem_read(esp + 4, 8))
            lookups.append((kind, attachment))
            uc.reg_write(reg.UC_X86_REG_EAX, lookup_value)
        uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
        uc.reg_write(reg.UC_X86_REG_EIP, ret)

    hook = cpu.hook_add(unicorn.UC_HOOK_CODE, intercept)
    try:
        for case, (head, count, fail) in enumerate(
                ((0, 0, False), (0x74028000, 12, False), (0x74028000, 12, True))):
            allocation_fails = fail
            allocations.clear()
            lookups.clear()
            owner_image = bytearray((i * 19 + case) & 0xff for i in range(OWNER_SIZE))
            struct.pack_into('<I', owner_image, 0x19c, head)
            struct.pack_into('<I', owner_image, 0x40, count)
            cpu.mem_write(owner, bytes(owner_image))
            cpu.mem_write(node, b'\xa5' * NODE_SIZE)
            try:
                result = oracle.call(0x52c190, this_pointer=owner,
                                     instruction_limit=20_000)
            except Exception as error:
                raise RuntimeError(('original driver insertion failed', case,
                                    hex(cpu.reg_read(reg.UC_X86_REG_EIP)),
                                    allocations, lookups)) from error
            expected = None if fail else build_default_driver_node(
                node, head, count, lambda *_: lookup_value)
            expected_return = 0 if fail else node
            actual_return = cpu.reg_read(reg.UC_X86_REG_EAX)
            if actual_return != expected_return:
                raise AssertionError(('return', case, hex(actual_return),
                                      hex(expected_return)))
            actual_owner = bytes(cpu.mem_read(owner, OWNER_SIZE))
            wanted_owner = bytearray(owner_image)
            if expected:
                struct.pack_into('<I', wanted_owner, 0x19c, expected.head)
                struct.pack_into('<I', wanted_owner, 0x40, expected.count)
            if actual_owner != bytes(wanted_owner):
                changed = [i for i, (a, b) in enumerate(zip(actual_owner, wanted_owner))
                           if a != b]
                raise AssertionError(('owner writes', case, changed[:16]))
            pool_value, = struct.unpack('<I', cpu.mem_read(0xa52be8, 4))
            expected_allocations = [(b'tPartInfo', NODE_SIZE, pool_value)]
            if allocations != expected_allocations:
                raise AssertionError(('allocator', case, allocations, expected_allocations))
            expected_lookups = [] if fail else [(0x80e9, 0)]
            if lookups != expected_lookups:
                raise AssertionError(('lookups', case, lookups, expected_lookups))
            if expected:
                actual_node = bytes(cpu.mem_read(node, NODE_SIZE))
                if actual_node != expected.node.image:
                    offset = next(i for i, (a, b) in enumerate(zip(actual_node,
                                                                    expected.node.image))
                                  if a != b)
                    raise AssertionError(('node bytes', case, hex(offset),
                                          actual_node[offset:offset + 16],
                                          expected.node.image[offset:offset + 16]))
    finally:
        cpu.hook_del(hook)
    return {'cases': 3, 'successful_insertions': 2, 'allocation_failures': 1,
            'maximum_byte_error': 0, 'original_entry': '0x52c190',
            'scope': 'complete successful default Driver tPartInfo image and owner prepend/count writes; allocator and class/attachment lookup stubbed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    print(verify(args.executable))


if __name__ == '__main__':
    main()
