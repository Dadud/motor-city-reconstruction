"""Compare the 0x52add0 component-node builder against original memory writes."""
import argparse
from pathlib import Path
import struct

from client.model_owner import build_component_node_list
from tools.native_oracle import DynoOracle
from unicorn import UC_HOOK_CODE

OWNER_SIZE = 0x878
NODE_SIZE = 0x984


def _template(class_id, attachment_id, marker, bounds):
    image = bytearray([marker]) * NODE_SIZE
    struct.pack_into('<I', image, 0x18, attachment_id)
    struct.pack_into('<II', image, 0x104, *bounds)
    struct.pack_into('<I', image, 0x338, class_id)
    return bytes(image)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    reg = oracle.reg
    base = 0x74000000
    cpu.mem_map(base, 0x40000)
    owner = base + 0x1000
    templates_address = base + 0x3000
    allocation_base = base + 0x10000
    allocation_stride = 0x1000
    allocation_index = 0
    lookup_calls = []
    free_calls = []

    def part_handle(class_id, attachment_id):
        lookup_calls.append((class_id, attachment_id))
        return 0x73000000 + class_id * 0x10 + attachment_id

    def intercept(uc, address, _size, _user_data):
        nonlocal allocation_index
        if address not in (0x6ee530, 0x528a70, 0x6ee550):
            return
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        return_address, = struct.unpack('<I', uc.mem_read(esp, 4))
        if address == 0x6ee530:
            _, size, _pool = struct.unpack('<III', uc.mem_read(esp + 4, 12))
            if size != NODE_SIZE:
                raise AssertionError(('unexpected allocation size', hex(size)))
            pointer = allocation_base + allocation_index * allocation_stride
            allocation_index += 1
            uc.reg_write(reg.UC_X86_REG_EAX, pointer)
        elif address == 0x528a70:
            class_id, attachment_id = struct.unpack('<II', uc.mem_read(esp + 4, 8))
            uc.reg_write(reg.UC_X86_REG_EAX,
                         part_handle(class_id, attachment_id))
        elif address == 0x6ee550:
            pointer, = struct.unpack('<I', uc.mem_read(esp + 4, 4))
            free_calls.append(pointer)
            uc.reg_write(reg.UC_X86_REG_EAX, 0)
        else:
            return
        # These are caller-cleaned helpers. Emulate their RET while preserving
        # the arguments for the original caller's own stack adjustment.
        uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
        uc.reg_write(reg.UC_X86_REG_EIP, return_address)

    cpu.hook_add(UC_HOOK_CODE, intercept)
    cases = (
        (_template(20001, 10, 0xA1, (0x11111111, 0x22222222)),),
        (_template(34001, 11, 0xB2, (0x33333333, 0x44444444)),
         _template(40001, 0, 0xC3, (0x55555555, 0x66666666))),
        (_template(17001, 0, 0xD4, (0x77777777, 0x88888888)),
         _template(1001, 5, 0xE5, (0x99999999, 0xAAAAAAAA)),
         _template(29001, 0, 0xF6, (0xBBBBBBBB, 0xCCCCCCCC))),
    )
    comparisons = 0
    for case_index, images in enumerate(cases):
        allocation_index = 0
        lookup_calls.clear()
        free_calls.clear()
        owner_image = bytearray((index * 17 + case_index) & 0xff
                                for index in range(OWNER_SIZE))
        struct.pack_into('<I', owner_image, 0x40, 7 + case_index)
        struct.pack_into('<I', owner_image, 0x19c, 0)
        cpu.mem_write(owner, bytes(owner_image))
        for index, image in enumerate(images):
            cpu.mem_write(templates_address + index * NODE_SIZE, image)
        addresses = tuple(allocation_base + index * allocation_stride
                          for index in range(len(images)))
        expected = build_component_node_list(
            images, addresses,
            lambda kind, attachment: 0x73000000 + kind * 0x10 + attachment)
        result = oracle.call(0x52add0, (owner, templates_address, len(images)),
                             instruction_limit=10_000)
        actual_result = cpu.reg_read(reg.UC_X86_REG_EAX)
        if actual_result != owner:
            raise AssertionError((case_index, 'return', hex(actual_result), hex(owner)))

        expected_owner = bytearray(owner_image)
        struct.pack_into('<I', expected_owner, 0x40, 7 + case_index + len(images))
        struct.pack_into('<I', expected_owner, 0x19c, expected.head)
        actual_owner = bytes(cpu.mem_read(owner, OWNER_SIZE))
        if actual_owner != bytes(expected_owner):
            changed = [i for i, pair in enumerate(zip(actual_owner, expected_owner))
                       if pair[0] != pair[1]]
            raise AssertionError((case_index, 'owner bytes', changed[:16]))
        for index, node in enumerate(expected.nodes):
            actual = bytes(cpu.mem_read(node.address, NODE_SIZE))
            if actual != node.image:
                changed = [i for i, pair in enumerate(zip(actual, node.image))
                           if pair[0] != pair[1]]
                raise AssertionError((case_index, index, 'node bytes', changed[:16]))
        expected_lookups = [(struct.unpack_from('<I', image, 0x338)[0],
                             struct.unpack_from('<I', image, 0x18)[0])
                            for image in images]
        if lookup_calls != expected_lookups or free_calls:
            raise AssertionError((case_index, lookup_calls, free_calls))
        comparisons += 1
    return {'cases': comparisons, 'templates': sum(map(len, cases)),
            'max_error': 0, 'original_entry': '0x52add0',
            'scope': 'existing empty owner; exact copied tPartInfo node images, class/attachment lookup, prepend links and owner head/count writes; allocator and lookup calls stubbed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(verify(args.executable))


if __name__ == '__main__':
    main()
