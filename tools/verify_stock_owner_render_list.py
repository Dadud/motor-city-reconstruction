"""Compare an installed stock vehicle through original 0x52dd70."""
import argparse
import struct
from pathlib import Path

from client.assembly import collect_body_render_records, stock_body_flags
from client.assets import Assets
from client.catalogue import Catalogue
from client.fce import Model, decode
from client.mechanical_parts import expand_mechanical_parts
from client.model_owner import build_stock_component_node_list
from client.render_list import build_render_list
from client.scene import ComponentModelNode, DRIVER_MODEL_BY_VARIANT, collect_component_render_graph
from tools.inspect_stock_mechanical import stock_slots
from tools.native_oracle import DynoOracle
from tools.verify_mechanical_presentation import _initialize_model_prefix


def verify(executable, game_root, vehicle_id=101, lod=0):
    import unicorn
    from unicorn import x86_const

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    prefix = _initialize_model_prefix(oracle, game_root)
    model_prefix_text = prefix.decode('cp1252')
    assets = Assets(game_root)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    slots = stock_slots(catalogue, vehicle_id, percent_damage=0, item_wear=0)
    parts = expand_mechanical_parts(slots, model_prefix=prefix)
    base = 0x74000000
    cpu.mem_map(base, 0x2000000)
    allocation = base + 0x1f00000
    node_addresses = tuple(base + 0x30000 + i * 0x1000 for i in range(len(parts)))
    driver_address = base + 0x30000 + len(parts) * 0x1000
    stock = build_stock_component_node_list(
        slots, node_addresses,
        lambda kind, attachment: 0x73000000 + kind * 0x10 + attachment,
        model_prefix=prefix, driver_node_address=driver_address)
    nodes = tuple(reversed(stock.component_nodes.nodes))
    loaded = {}
    unloaded = []
    for record in nodes:
        image = record.image
        class_index = struct.unpack_from('<I', image, 0x338)[0]
        attachment = struct.unpack_from('<I', image, 0x18)[0]
        path = image[0x22c:0x32c].split(b'\0', 1)[0].decode('cp1252')
        model = None
        if path and not path.startswith('.'):
            relative = (path[len(model_prefix_text):]
                        if path.casefold().startswith(model_prefix_text.casefold())
                        else path)
            asset_key = ('data/models/' + relative.replace('\\', '/')).casefold()
            asset_path = assets.paths.get(asset_key)
            if asset_path is not None:
                try:
                    model_image = assets.load_vehicle_bytes(asset_path)
                    model = decode(model_image)
                except (KeyError, ValueError) as error:
                    unloaded.append((class_index, attachment, path, str(error)))
                    model = None
                    model_image = None
        if class_index == 0x80e9:
            driver_path = assets.paths[
                ('data/models/' + DRIVER_MODEL_BY_VARIANT[0] + '.viv').casefold()]
            model_image = assets.load_vehicle_bytes(driver_path)
            model = decode(model_image)
        if model is None:
            continue
        if model is not None:
            loaded[record.address] = (model, model_image)

    body_filename = catalogue.vehicle(vehicle_id).body_filename
    body_key = ('data/models/' + body_filename + '.viv').casefold()
    body_path = assets.paths.get(body_key)
    if body_path is None:
        raise ValueError(f'stock body archive is missing: {body_key}')
    body = assets.load_vehicle(body_path)
    flags = stock_body_flags(body, catalogue.vehicle(vehicle_id).parts)
    body_address = 0
    model_images = {}
    actual_nodes = []
    oracle_nodes = []
    model_cursor = base + 0x200000
    component_node_count = 0
    for index, record in enumerate(nodes):
        class_id = struct.unpack_from('<I', record.image, 0x338)[0]
        attachment = struct.unpack_from('<I', record.image, 0x18)[0]
        model, image = loaded.get(record.address, (Model((), 0), None))
        address = base + 0x100000 + index * 0x1000
        if image is None:
            model_address = 0
        else:
            model_address = model_cursor
            model_cursor += ((len(image) + 0xfff) // 0x1000 + 1) * 0x1000
            model_images[model_address] = image
            component_node_count += 1
        class_index = attachment if attachment < 12 else 0
        node = ComponentModelNode(class_index, model, model_address, class_id)
        actual_nodes.append((address, model_address, node, record))
        oracle_nodes.append(node)
        if class_id == 0x4e21:
            body_address = model_address
    if not body_address:
        raise ValueError('stock tPartInfo list has no resolved body model node')
    # The component records are already prepended in native owner-list order.
    for index, (address, model_address, node, record) in enumerate(actual_nodes):
        following = actual_nodes[index + 1][0] if index + 1 < len(actual_nodes) else 0
        native_image = bytearray(actual_nodes[index][3].image)
        struct.pack_into('<II', native_image, 0, following, model_address)
        cpu.mem_write(address, bytes(native_image))
    owner = base + 0x70000
    owner_image = bytearray(0x300)
    struct.pack_into('<I', owner_image, 0x19c,
                     actual_nodes[0][0] if actual_nodes else 0)
    struct.pack_into('<I', owner_image, 0x22c, flags)
    allocation_requests = []
    def allocation_boundary(uc, address, _size, _user_data):
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        tag_ptr, size, _pool = struct.unpack('<III', uc.mem_read(esp, 12))
        if tag_ptr != 0x895e48 or size > 0x10000:
            raise AssertionError(('allocator arguments', hex(tag_ptr), size))
        allocation_requests.append(size)
        uc.mem_write(allocation, bytes(size))
        uc.reg_write(reg.UC_X86_REG_EAX, allocation)
        uc.reg_write(reg.UC_X86_REG_EIP, 0x52de31)

    for model_address, image in model_images.items():
        cpu.mem_write(model_address, image)
    cpu.mem_write(owner, bytes(owner_image))
    hook = cpu.hook_add(unicorn.UC_HOOK_CODE, allocation_boundary,
                        begin=0x52de2c, end=0x52de2c)
    try:
        oracle.call(0x52dd70, (lod,), this_pointer=owner, cleanup=b'',
                    instruction_limit=10_000_000)
        result = cpu.reg_read(x86_const.UC_X86_REG_EAX)
    finally:
        cpu.hook_del(hook)
    graph = collect_component_render_graph(body, tuple(oracle_nodes), lod, flags)
    body_records = collect_body_render_records(body, flags & (0xfffeffff if lod > 2 else 0xffffffff),
                                               min(lod, 3), include_interior=(lod < 3))
    expected = build_render_list(body_records + tuple(entry.record for entry in graph.entries)).records
    if not expected:
        if result != 0 or allocation_requests:
            raise AssertionError(('unexpected native render list', hex(result), allocation_requests))
    else:
        if result != allocation or allocation_requests != [len(expected) * 36]:
            count = allocation_requests[-1] // 36 if allocation_requests else 0
            native_records = [struct.unpack('<9I', cpu.mem_read(allocation + i * 36, 36))
                              for i in range(count)]
            raise AssertionError(('allocation result', hex(result), allocation_requests,
                                  len(expected), 'native', native_records,
                                  'portable', [record.words for record in expected],
                                  'unloaded', unloaded,
                                  'graph', [(entry.marker_path, entry.node_index,
                                             entry.part_index, entry.record.words[5])
                                            for entry in graph.entries]))
        for index, record in enumerate(expected):
            actual = struct.unpack('<9I', cpu.mem_read(allocation + index * 36, 36))
            wanted = list(record.words)
            wanted[0] = allocation + (index + 1) * 36 if index + 1 < len(expected) else 0
            if wanted[1] == 0:
                wanted[1] = body_address
            if actual != tuple(wanted):
                raise AssertionError(('record', index, actual, tuple(wanted)))
    origin_checks = 0
    for index, (address, model_handle, node, record) in enumerate(actual_nodes):
        if not model_handle:
            continue
        original_model = loaded[record.address][0]
        changed_model = graph.models[index]
        actual_image = bytes(cpu.mem_read(node.model_handle,
                                          len(loaded[record.address][1])))
        if len(original_model.parts) != len(changed_model.parts):
            raise AssertionError(('component part count changed', index))
        for part_index, (original_part, changed_part) in enumerate(
                zip(original_model.parts, changed_model.parts)):
            actual_origin = struct.unpack_from('<3f', actual_image,
                                               0x120 + part_index * 12)
            if actual_origin != changed_part.origin:
                raise AssertionError(('component origin mutation', index,
                                      part_index, actual_origin,
                                      changed_part.origin))
            origin_checks += 1
    return {'vehicle_id': vehicle_id, 'body': body_filename, 'lod': lod, 'owner_flags': hex(flags),
            'owner_nodes': len(nodes), 'loaded_component_nodes': component_node_count,
            'loaded_models': len(model_images), 'records': len(expected),
            'component_origin_checks': origin_checks,
            'native_result': hex(result), 'allocations': allocation_requests,
            'scope': 'installed stock owner nodes, stock body and VIV FCE models compared through original 0x52dd70; resource lookup and allocation boundary supplied by fixture'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--game-root', required=True, type=Path)
    parser.add_argument('--vehicle-id', default=101, type=int)
    parser.add_argument('--lod', default=0, type=int)
    parser.add_argument('--all-lods', action='store_true',
                        help='compare requested LOD values 0 through 4')
    args = parser.parse_args()
    lods = range(5) if args.all_lods else (args.lod,)
    for lod in lods:
        print(verify(args.executable, args.game_root, args.vehicle_id, lod))


if __name__ == '__main__':
    main()
