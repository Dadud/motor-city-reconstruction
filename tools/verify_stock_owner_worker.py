"""Compare the ready-success path of stock owner worker `0x52c790`."""
import argparse
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.mechanical_parts import expand_mechanical_parts
from client.model_owner import complete_ready_stock_owner_job
from tools.inspect_stock_mechanical import stock_slots
from tools.native_oracle import DynoOracle
from tools.verify_component_node_list import OWNER_SIZE, NODE_SIZE
from tools.verify_mechanical_presentation import _initialize_model_prefix


def verify(executable, game_root, vehicle_id=101, *, exercise_selected_slot=False):
    import unicorn

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    prefix = _initialize_model_prefix(oracle, game_root)
    # The prefix initializer maps the low SEH registration page required by
    # original 0x52c6b0 before this call is reached.
    base = 0x74000000
    cpu.mem_map(base, 0x200000)
    owner, completion, job = base + 0x1000, base + 0x2000, base + 0x3000
    source = base + 0x10000
    scratch = base + 0x30000
    node_base = base + 0x70000
    node_stride = 0x1000

    assets = Assets(game_root)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    slots = stock_slots(catalogue, vehicle_id, percent_damage=0, item_wear=0)
    if exercise_selected_slot:
        first = bytearray(slots[0])
        struct.pack_into('<I', first, 0, 0x65)
        slots = (bytes(first),) + tuple(slots[1:])
    part_count = len(expand_mechanical_parts(slots, model_prefix=prefix))
    if part_count > 100:
        raise AssertionError(('unexpected stock node count', part_count))
    cpu.mem_write(source, b''.join(slots))

    owner_image = bytearray((i * 23 + 5) & 0xff for i in range(OWNER_SIZE))
    struct.pack_into('<I', owner_image, 0x40, 0)
    struct.pack_into('<I', owner_image, 0x170, base + 0x7000)
    struct.pack_into('<I', owner_image, 0x174, 0)
    struct.pack_into('<I', owner_image, 0x178, 0)
    struct.pack_into('<I', owner_image, 0x19c, 0)
    owner_image[0x17c] = 0
    owner_image[0x190] = 0
    cpu.mem_write(owner, bytes(owner_image))

    job_image = bytearray(0xbc0)
    struct.pack_into('<I', job_image, 0x04, len(slots))
    struct.pack_into('<I', job_image, 0x08, source)
    struct.pack_into('<I', job_image, 0x58, base + 0x7100)
    struct.pack_into('<I', job_image, 0x5c, base + 0x7200)
    for i in range(12):
        struct.pack_into('<I', job_image, 0x68 + i * 4, 0xA5000000 + i)
    job_image[0x1d7:0x1e4] = b'ready status\0'
    struct.pack_into('<I', job_image, 0xbb0, 0x12345678)
    cpu.mem_write(job, bytes(job_image))
    completion_image = bytearray(0x20)
    struct.pack_into('<I', completion_image, 0x04, 1)
    struct.pack_into('<I', completion_image, 0x08, job)
    cpu.mem_write(completion, bytes(completion_image))

    driver_type = owner_image[0x17c]
    driver_ptr, = struct.unpack('<I', cpu.mem_read(0x83de58 + driver_type * 0x24, 4))
    driver_key = bytes(cpu.mem_read(driver_ptr, 64)).split(b'\0', 1)[0]
    driver_size, = struct.unpack('<I', cpu.mem_read(0x83de60 + driver_type * 0x24, 4))
    expected = complete_ready_stock_owner_job(
        bytes(owner_image), slots, bytes(job_image),
        tuple(node_base + i * node_stride for i in range(part_count)),
        node_base + part_count * node_stride,
        lambda kind, attachment: 0x73000000 + kind * 0x10 + attachment,
        model_prefix=prefix, driver_model_key=driver_key, driver_size=driver_size)

    allocations, lookups, releases = [], [], []
    cursor = scratch
    node_index = 0
    scratch_size = len(slots) * 0x1308

    def intercept(uc, address, _size, _user):
        nonlocal cursor, node_index
        if address == 0x52c7d0:  # GetCurrentThreadId import call; ready case never sleeps.
            uc.reg_write(reg.UC_X86_REG_EAX, 0x1234)
            uc.reg_write(reg.UC_X86_REG_EIP, address + 6)
            return
        if address == 0x66df20:
            esp = uc.reg_read(reg.UC_X86_REG_ESP)
            ret, _handle, output_ptr, _flag = struct.unpack('<IIII', uc.mem_read(esp, 16))
            uc.mem_write(output_ptr, struct.pack('<I', completion))
            uc.reg_write(reg.UC_X86_REG_EAX, 0)
            uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
            uc.reg_write(reg.UC_X86_REG_EIP, ret)
            return
        if address == 0x6ee530:
            esp = uc.reg_read(reg.UC_X86_REG_ESP)
            ret, tag_ptr, size, pool = struct.unpack('<IIII', uc.mem_read(esp, 16))
            tag = bytes(uc.mem_read(tag_ptr, 32)).split(b'\0', 1)[0]
            allocations.append((tag, size, pool))
            if size == scratch_size and tag == b'PARTS':
                result = scratch
            elif size == NODE_SIZE:
                result = node_base + node_index * node_stride
                node_index += 1
            else:
                raise AssertionError(('unexpected allocation', tag, size, pool))
            uc.reg_write(reg.UC_X86_REG_EAX, result)
            uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
            uc.reg_write(reg.UC_X86_REG_EIP, ret)
            return
        if address == 0x528a70:
            esp = uc.reg_read(reg.UC_X86_REG_ESP)
            ret, kind, attachment = struct.unpack('<III', uc.mem_read(esp, 12))
            lookups.append((kind, attachment))
            uc.reg_write(reg.UC_X86_REG_EAX,
                         0x73000000 + kind * 0x10 + attachment)
            uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
            uc.reg_write(reg.UC_X86_REG_EIP, ret)
            return
        if address in (0x489b20, 0x6ee550, 0x66df80):
            esp = uc.reg_read(reg.UC_X86_REG_ESP)
            ret, arg = struct.unpack('<II', uc.mem_read(esp, 8))
            releases.append((address, arg))
            uc.reg_write(reg.UC_X86_REG_EAX, 0)
            # 0x489b20 is thiscall-like and cleans its one stack argument.
            uc.reg_write(reg.UC_X86_REG_ESP, esp + (8 if address == 0x489b20 else 4))
            uc.reg_write(reg.UC_X86_REG_EIP, ret)

    hook = cpu.hook_add(unicorn.UC_HOOK_CODE, intercept)
    try:
        oracle.call(0x52c790, this_pointer=owner, instruction_limit=2_000_000)
    except Exception as error:
        raise RuntimeError(('0x52c790 original run failed',
                            hex(cpu.reg_read(reg.UC_X86_REG_EIP)), allocations,
                            lookups, releases)) from error
    finally:
        cpu.hook_del(hook)

    result = cpu.reg_read(reg.UC_X86_REG_EAX)
    if result != 1:
        raise AssertionError(('worker return', result))
    actual_owner = bytes(cpu.mem_read(owner, OWNER_SIZE))
    if actual_owner != expected.owner_image:
        changed = [i for i, (a, b) in enumerate(zip(actual_owner, expected.owner_image))
                   if a != b]
        raise AssertionError(('owner image', changed[:32],
                              actual_owner[:48], expected.owner_image[:48],
                              [(hex(i), actual_owner[i:i+8], expected.owner_image[i:i+8])
                               for i in changed[:8]]))
    actual_nodes = []
    for expected_node in expected.component_nodes.nodes:
        actual = bytes(cpu.mem_read(expected_node.address, NODE_SIZE))
        if actual != expected_node.image:
            offset = next(i for i, (a, b) in enumerate(zip(actual, expected_node.image))
                          if a != b)
            raise AssertionError(('node', hex(expected_node.address), hex(offset),
                                  actual[offset:offset + 16],
                                  expected_node.image[offset:offset + 16]))
        actual_nodes.append(actual)
    expected_lookups = [(
        struct.unpack_from('<I', part.image, 0x338)[0],
        struct.unpack_from('<I', part.image, 0x18)[0])
        for part in expand_mechanical_parts(slots, model_prefix=prefix)] + [(0x80e9, 0)]
    if lookups != expected_lookups:
        raise AssertionError(('lookup sequence', lookups, expected_lookups))
    expected_releases = [(0x489b20, struct.unpack_from('<I', job_image, 0x58)[0]),
                         (0x6ee550, scratch), (0x66df80, completion)]
    if releases != expected_releases:
        raise AssertionError(('release sequence', releases, expected_releases))
    if node_index != len(expected.component_nodes.nodes):
        raise AssertionError(('allocated owner nodes', node_index,
                              len(expected.component_nodes.nodes)))
    return {'vehicle_id': vehicle_id, 'source_slots': len(slots),
            'mechanical_records': part_count, 'owner_nodes': len(actual_nodes),
            'selected_source_index': expected.source_vehicle_index,
            'driver_model_key': driver_key.decode('ascii'),
            'driver_model_size': driver_size, 'allocation_calls': len(allocations),
            'original_result': result, 'maximum_byte_error': 0,
            'original_entry': '0x52c790',
            'scope': 'ready successful stock worker flow through original 0x52c6b0, 0x52c550, 0x52c2e0, 0x52add0, 0x52c190, 0x530a90, 0x699330 and 0x52ca30; worker queue, allocator, resource lookup/release stubbed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--game-root', required=True)
    parser.add_argument('--vehicle-id', type=int, default=101)
    parser.add_argument('--exercise-selected-slot', action='store_true')
    args = parser.parse_args()
    print(verify(args.executable, args.game_root, args.vehicle_id,
                 exercise_selected_slot=args.exercise_selected_slot))


if __name__ == '__main__':
    main()
