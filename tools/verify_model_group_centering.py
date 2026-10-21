"""Compare the prepared geometry phase of original model startup 0x52be40."""
import argparse
import json
import random
import struct
from pathlib import Path

from client.model_group_centering import (PreparedModelGroup, SelectedPart,
                                           prepare_model_group)
from client.model_group_centering import (TireModelComponent,
                                           prepare_tire_models)
from client.model_group_centering import prepare_rear_suspension_model
from client.model_group_centering import prepare_vehicle_model_group
from tools.native_oracle import DynoOracle


def build_image(origin=(10.,20.,30.), vertices=((0.,0.,0.),(2.,4.,6.)),
                dummies=((1.,2.,3.),)):
    out = bytearray(0x2038 + len(vertices)*12)
    struct.pack_into('<4I', out, 0, 0x101015, 0, 0, len(vertices))
    struct.pack_into('<I', out, 0x14, 0)
    struct.pack_into('<I', out, 0x34, len(vertices)*12)
    struct.pack_into('<I', out, 0x2c, len(vertices)*24)
    struct.pack_into('<I', out, 0x58, len(dummies))
    struct.pack_into('<I', out, 0x11c, 1)
    struct.pack_into('<3f', out, 0x120, *origin)
    struct.pack_into('<I', out, 0x520, len(vertices))
    for index, point in enumerate(vertices):
        struct.pack_into('<3f', out, 0x2038+index*12, *point)
    for index, point in enumerate(dummies):
        struct.pack_into('<3f', out, 0x5c+index*12, *point)
    out[0xe28:0xe2d] = b':body'
    return out


def model_fixture(rng, origin, *, empty=False):
    if empty:
        vertices = ()
    else:
        vertices = tuple(tuple(rng.uniform(-4, 4) for _ in range(3))
                         for _ in range(rng.randint(1, 7)))
    dummies = tuple(tuple(rng.uniform(-3, 3) for _ in range(3))
                    for _ in range(rng.randint(0, 3)))
    out = bytearray(build_image(origin, vertices, dummies))
    return out


def verify(executable, cases=128):
    if not 1 <= cases <= 4096:
        raise ValueError('case count must be from 1 to 4096')
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    memory, owner, output = 0x74000000, 0x74001000, oracle.inputs
    cpu.mem_map(memory, 0x100000)
    rng = random.Random(0x52be40)
    max_cases = 0
    for case in range(cases):
        # A single owner node gives a complete isolated model image without
        # claiming the still-unresolved cross-node attachment graph layout.
        model_count = 1
        models = [model_fixture(rng,
            tuple(rng.uniform(-20, 20) for _ in range(3)), empty=(rng.randrange(7) == 0))
            for _ in range(model_count)]
        component_nodes = [memory+0x30000+i*0x400 for i in range(model_count)]
        selected_nodes = [memory+0x31000+i*0x400 for i in range(model_count)]
        model_addresses = [memory+0x10000+i*0x8000 for i in range(model_count)]
        for address, model in zip(model_addresses, models):
            cpu.mem_write(address, bytes(model))
        selections = []
        selected_info = []
        for index, address in enumerate(model_addresses):
            model = models[index]
            part_count = struct.unpack_from('<I', model, 0x11c)[0]
            if part_count and rng.randrange(4) != 0:
                flags = 0
                kind = 0
                selected_info.append((0, flags, kind))
                selections.append(SelectedPart(index, 0, flags, kind))
            else:
                selected_info.append((-1, 0, 0))
            component = component_nodes[index]
            selected = selected_nodes[index]
            cpu.mem_write(component, bytes(0x33c))
            cpu.mem_write(selected, bytes(0x33c))
            cpu.mem_write(component, struct.pack('<II',
                component_nodes[index+1] if index+1 < model_count else 0, address))
            cpu.mem_write(selected, struct.pack('<II',
                selected_nodes[index+1] if index+1 < model_count else 0, address))
            # Tire/suspension preparation skips non-component class IDs.
            cpu.mem_write(component+0x338, struct.pack('<I', 0))
            part, flags, kind = selected_info[-1]
            cpu.mem_write(selected+0x0c, struct.pack('<h', part))
            cpu.mem_write(selected+0x10, struct.pack('<I', flags))
            cpu.mem_write(selected+0x14, struct.pack('<I', kind))
        group = PreparedModelGroup(tuple(bytes(m) for m in models),
            tuple(range(model_count)), tuple(selections), 0x40)
        cpu.mem_write(owner, bytes(0x400))
        cpu.mem_write(owner+0x19c, struct.pack('<I', component_nodes[0]))
        cpu.mem_write(owner+0x21c, struct.pack('<I', selected_nodes[0]))
        cpu.mem_write(owner+0x22c, struct.pack('<I', group.owner_flags))
        cpu.mem_write(output, bytes(12))
        try:
            oracle.call(0x52be40, (output,), this_pointer=owner,
                        cleanup=b'', instruction_limit=1_000_000)
        except Exception as error:
            eip = cpu.reg_read(reg.UC_X86_REG_EIP)
            raise RuntimeError(f'original execution fault at 0x{eip:08x} in case {case}') from error
        expected = prepare_model_group(group)
        observed_models = tuple(bytes(cpu.mem_read(address, len(source)))
                                for address, source in zip(model_addresses, models))
        if observed_models != expected.group.models:
            source, observed, wanted = models[0], observed_models[0], expected.group.models[0]
            offsets = [i for i, (left, right) in enumerate(zip(observed, wanted)) if left != right]
            raise AssertionError((case, 'model-image mismatch', selections, group.owner_flags,
                offsets[:20], struct.unpack_from('<3f', source, 0x120),
                struct.unpack_from('<3f', observed, 0x120),
                struct.unpack_from('<3f', wanted, 0x120)))
        observed_extents = struct.unpack('<3f', bytes(cpu.mem_read(output, 12)))
        if struct.pack('<3f', *observed_extents) != struct.pack('<3f', *expected.half_extents):
            raise AssertionError((case, 'extent mismatch', observed_extents, expected.half_extents))
        max_cases += 1
    return dict(cases=max_cases, max_error=0,
        original_entry='0x52be40',
        scope='single prepared non-tire model node; compares the entire FCE image and output half-extents. Tire/suspension placement takes observed no-match paths; multi-node attachment graph is unverified.')


def verify_stock_bodies(executable, game):
    """Exercise the original centering entry on installed stock body FCE files."""
    from client.assets import Assets
    from client.catalogue import Catalogue
    from tools.viv import read_member
    assets = Assets(game)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    bodies = {}
    for vehicle_id in range(101, 109):
        name = catalogue.vehicle(vehicle_id).body_filename.casefold()
        bodies.setdefault(name, assets.paths[f'data/models/{name}.viv'])
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    memory, owner, component, selection = 0x74000000, 0x74001000, 0x74200000, 0x74201000
    model_address, output = 0x74010000, oracle.inputs
    cpu.mem_map(memory, 0x1000000)
    results = []
    for name, path in sorted(bodies.items()):
        source = read_member(path, 'part.fce')
        part_count = struct.unpack_from('<I', source, 0x11c)[0]
        if not 1 <= part_count <= 64 or len(source) > 0x800000:
            raise ValueError(f'{name}: stock body exceeds bounded model domain')
        cpu.mem_write(model_address, source)
        cpu.mem_write(component, bytes(0x33c))
        cpu.mem_write(component, struct.pack('<II', 0, model_address))
        cpu.mem_write(component+0x338, struct.pack('<I', 0))
        for part in range(part_count):
            node = selection + part*0x400
            cpu.mem_write(node, struct.pack('<II',
                node+0x400 if part+1 < part_count else 0, model_address))
            cpu.mem_write(node+0x0c, struct.pack('<h', part))
            cpu.mem_write(node+0x10, struct.pack('<I', 0))
            cpu.mem_write(node+0x14, struct.pack('<I', 0))
        owner_image = bytearray(0x400)
        struct.pack_into('<I', owner_image, 0x19c, component)
        struct.pack_into('<I', owner_image, 0x21c, selection)
        struct.pack_into('<I', owner_image, 0x22c, 0x40)
        cpu.mem_write(owner, bytes(owner_image))
        cpu.mem_write(output, bytes(12))
        oracle.call(0x52be40, (output,), this_pointer=owner, cleanup=b'',
                    instruction_limit=1_000_000)
        expected = prepare_model_group(PreparedModelGroup(
            (source,), (0,), tuple(SelectedPart(0, part) for part in range(part_count)),
            0x40))
        observed = bytes(cpu.mem_read(model_address, len(source)))
        extents = bytes(cpu.mem_read(output, 12))
        if observed != expected.group.models[0] or extents != struct.pack('<3f',
                *expected.half_extents):
            changed = [offset for offset, (left, right) in enumerate(zip(
                observed, expected.group.models[0])) if left != right]
            raise AssertionError((name, 'stock FCE mismatch',
                struct.unpack('<3f', extents), expected.half_extents,
                changed[:24], len(changed)))
        results.append(dict(body=name, parts=part_count, source_bytes=len(source)))
    return dict(cases=len(results), models=results, max_error=0,
        original_entry='0x52be40',
        scope='all selected parts in each unique stock body FCE for vehicles 101-108; compares entire FCE and output extents; component attachments remain outside this test')


def verify_stock_body_collector(executable, game):
    """Connect recovered stock body flags/collector records to 0x52be40."""
    from client.assets import Assets
    from client.catalogue import Catalogue
    from client.assembly import stock_body_flags, collect_body_render_records
    from client.fce import decode
    from tools.viv import read_member
    assets=Assets(game);catalogue=Catalogue.load(assets.paths['data/db/online.mdb'])
    oracle=DynoOracle(executable);cpu=oracle.cpu
    memory,owner,component,selection=0x74000000,0x74001000,0x74200000,0x74201000
    model_address,output=0x74010000,oracle.inputs
    cpu.mem_map(memory,0x1000000);reports=[]
    for vehicle_id in range(101,109):
        vehicle=catalogue.vehicle(vehicle_id)
        path=assets.paths[f'data/models/{vehicle.body_filename.casefold()}.viv']
        source=read_member(path,'part.fce');model=decode(source)
        flags=stock_body_flags(model,vehicle.parts)
        records=collect_body_render_records(model,flags,0,include_interior=True)
        selected=[]
        for record in records:
            part=record.words[3]
            if part >= len(model.parts) or not model.parts[part].vertices:
                continue
            selected.append((part,record.words[4],record.words[5]))
        if not selected:raise ValueError(f'{vehicle_id}: body collector selected no boundable surfaces')
        cpu.mem_write(model_address,source)
        cpu.mem_write(component,struct.pack('<II',0,model_address))
        cpu.mem_write(component+0x338,struct.pack('<I',0))
        for index,(part,record_flags,kind) in enumerate(selected):
            node=selection+index*0x400
            cpu.mem_write(node,struct.pack('<II',selection+(index+1)*0x400 if index+1<len(selected) else 0,model_address))
            cpu.mem_write(node+0x0c,struct.pack('<h',part))
            cpu.mem_write(node+0x10,struct.pack('<I',record_flags))
            cpu.mem_write(node+0x14,struct.pack('<I',kind))
        owner_image=bytearray(0x400)
        struct.pack_into('<I',owner_image,0x19c,component)
        struct.pack_into('<I',owner_image,0x21c,selection)
        struct.pack_into('<I',owner_image,0x22c,0x40)
        cpu.mem_write(owner,bytes(owner_image));cpu.mem_write(output,bytes(12))
        oracle.call(0x52be40,(output,),this_pointer=owner,cleanup=b'',instruction_limit=1_000_000)
        expected=prepare_model_group(PreparedModelGroup((source,),(0,),
            tuple(SelectedPart(0,part,record_flags,kind)
                  for part,record_flags,kind in selected),0x40))
        observed=bytes(cpu.mem_read(model_address,len(source)))
        extent=bytes(cpu.mem_read(output,12))
        if observed!=expected.group.models[0] or extent!=struct.pack('<3f',*expected.half_extents):
            raise AssertionError((vehicle_id,'collector model mismatch',
                struct.unpack('<3f',extent),expected.half_extents,
                next((i for i,(a,b) in enumerate(zip(observed,expected.group.models[0])) if a!=b),None)))
        reports.append(dict(vehicle=vehicle_id,body=vehicle.body_filename,
            selected_surfaces=len(selected),mirrored=sum(bool(f&0x40) for _,f,_ in selected),
            extent=expected.half_extents))
    return dict(cases=len(reports),vehicles=reports,max_error=0,original_entry='0x52be40',
        scope='stock body flags and 0x52d710 collector output connect to original selected-bound/centering path for vehicles 101-108; component attachments and original linked-node producer remain unresolved')


def verify_stock_vehicle_pipeline(executable, game):
    """Compare assembled stock body, tire and suspension FCEs in 0x52be40."""
    from client.assets import Assets
    from client.catalogue import Catalogue
    from tools.viv import read_member
    assets = Assets(game)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    memory, owner = 0x74000000, 0x74001000
    model_addresses = (0x74010000, 0x74100000, 0x74200000)
    nodes, selected_head = 0x74300000, 0x74301000
    output = oracle.inputs
    cpu.mem_map(memory, 0x400000)
    reports=[]
    for vehicle_id in range(101,109):
        vehicle=catalogue.vehicle(vehicle_id)
        by_kind={}
        for kind in (20001,110001,1001):
            part=next((part for part in vehicle.parts if part.abstract_type_id==kind),None)
            if part is None or not part.filename:
                raise ValueError(f'{vehicle_id}: missing stock model for component {kind}')
            by_kind[kind]=read_member(
                assets.paths[f'data/models/{part.filename.casefold()}.viv'],'part.fce')
        source_models=(
            read_member(assets.paths[
                f'data/models/{vehicle.body_filename.casefold()}.viv'],'part.fce'),
            by_kind[110001], by_kind[1001])
        parts=tuple(struct.unpack_from('<I',image,0x11c)[0] for image in source_models)
        if any(not 1 <= count <= 64 for count in parts):
            raise ValueError(f'{vehicle_id}: model part count outside the supported FCE domain')
        dims=catalogue.tire_dimensions(vehicle)['LR']
        components=(TireModelComponent(0,0,0),
            TireModelComponent(0x1adb1,3,1,dims.width_mm,dims.aspect_percent,dims.rim_inches),
            TireModelComponent(0x3e9,0,2))
        selected=tuple(SelectedPart(model_index,part_index)
            for model_index,count in enumerate(parts) for part_index in range(count))
        group=PreparedModelGroup(source_models,(0,1,2),selected,owner_flags=0x40)
        expected=prepare_vehicle_model_group(group,components)
        cpu.mem_write(owner,bytes(0x400))
        for index,(address,image,component) in enumerate(zip(
                model_addresses,source_models,components)):
            cpu.mem_write(address,image)
            node=nodes+index*0x400
            cpu.mem_write(node,struct.pack('<II',
                nodes+(index+1)*0x400 if index+1<len(components) else 0,address))
            cpu.mem_write(node+0x14,struct.pack('<I',component.position))
            cpu.mem_write(node+0x18,struct.pack('<I',component.position))
            cpu.mem_write(node+0x338,struct.pack('<I',component.class_id))
            if component.class_id==0x1adb1:
                cpu.mem_write(node+0x3c,struct.pack('<3f',dims.width_mm,
                    dims.aspect_percent,dims.rim_inches))
        cursor=selected_head
        emitted=[]
        for model_index,count in enumerate(parts):
            for part_index in range(count):
                emitted.append((cursor,model_index,part_index))
                cursor+=0x400
        for index,(address,model_index,part_index) in enumerate(emitted):
            node=nodes+model_index*0x400
            current=address
            nxt=emitted[index+1][0] if index+1<len(emitted) else 0
            cpu.mem_write(current,struct.pack('<II',nxt,model_addresses[model_index]))
            cpu.mem_write(current+0x0c,struct.pack('<h',part_index))
            cpu.mem_write(current+0x10,struct.pack('<I',0))
            cpu.mem_write(current+0x14,struct.pack('<I',0))
        cpu.mem_write(owner+0x19c,struct.pack('<I',nodes))
        cpu.mem_write(owner+0x21c,struct.pack('<I',selected_head))
        cpu.mem_write(owner+0x22c,struct.pack('<I',0x40))
        cpu.mem_write(output,bytes(12))
        oracle.call(0x52be40,(output,),this_pointer=owner,cleanup=b'',
                    instruction_limit=1_000_000)
        observed=tuple(bytes(cpu.mem_read(address,len(image))) for address,image in
                       zip(model_addresses,source_models))
        extents=bytes(cpu.mem_read(output,12))
        if observed!=expected.result.group.models or extents!=struct.pack('<3f',
                *expected.result.half_extents):
            raise AssertionError((vehicle_id,'stock component pipeline mismatch',
                [index for index,(actual,wanted) in enumerate(zip(observed,
                    expected.result.group.models)) if actual!=wanted],
                struct.unpack('<3f',extents),expected.result.half_extents))
        reports.append(dict(vehicle=vehicle_id,body=vehicle.body_filename,
            parts=parts,extent=expected.result.half_extents))
    return dict(cases=len(reports),vehicles=reports,max_error=0,
        original_entry='0x52be40',
        scope='installed stock body, tire and suspension FCEs plus catalogue tire dimensions for vehicles 101-108; three-component owner graph and all model parts compared byte-for-byte; synthetic one-wheel node mapping does not prove original stock list construction')


def verify_stock_wheel_preparation(executable, game):
    """Compare original 0x52b950 over stock tire+rim pairs at all corners."""
    from client.assets import Assets
    from client.catalogue import Catalogue
    from tools.viv import read_member
    assets = Assets(game)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    memory, owner, nodes = 0x74000000, 0x74001000, 0x74200000
    model_addresses = (0x74010000, 0x74100000)
    cpu.mem_map(memory, 0x400000)
    reports = []
    corners = (('LF', 1, 10, 1), ('RF', 2, 10, 2),
               ('LR', 3, 11, 3), ('RR', 4, 11, 4))
    for vehicle_id in range(101, 109):
        vehicle = catalogue.vehicle(vehicle_id)
        dimensions = catalogue.tire_dimensions(vehicle)
        for key, side, axle, position in corners:
            source_models, components, chosen = [], [], []
            for kind, node_class in ((110001, 0x1adb1), (100001, 0x186a1)):
                part = next((item for item in vehicle.parts
                    if item.abstract_type_id == kind and item.attachment_id == side), None)
                if part is None:
                    part = next((item for item in vehicle.parts
                        if item.abstract_type_id == kind and item.attachment_id == axle), None)
                if part is None or not part.filename:
                    raise ValueError((vehicle_id, key, 'missing tire/rim component', kind))
                path = assets.paths.get(f'data/models/{part.filename.casefold()}.viv')
                if path is None:
                    raise ValueError((vehicle_id, key, 'missing component archive', part.filename))
                model_index = len(source_models)
                source_models.append(read_member(path, 'part.fce'))
                chosen.append((kind, part.filename))
                if kind == 110001:
                    size = dimensions[key]
                    components.append(TireModelComponent(node_class, position,
                        model_index, size.width_mm, size.aspect_percent,
                        size.rim_inches))
                else:
                    components.append(TireModelComponent(node_class, position,
                        model_index))
            expected = prepare_tire_models(source_models, components, position)
            cpu.mem_write(owner, bytes(0x400))
            cpu.mem_write(owner+0x19c, struct.pack('<I', nodes))
            for index, (address, image, component) in enumerate(zip(
                    model_addresses, source_models, components)):
                node = nodes+index*0x400
                cpu.mem_write(address, image)
                cpu.mem_write(node, struct.pack('<II',
                    nodes+(index+1)*0x400 if index+1 < len(components) else 0,
                    address))
                cpu.mem_write(node+0x14, struct.pack('<I', position))
                cpu.mem_write(node+0x18, struct.pack('<I', position))
                cpu.mem_write(node+0x338, struct.pack('<I', component.class_id))
                if component.class_id == 0x1adb1:
                    cpu.mem_write(node+0x3c, struct.pack('<3f',
                        component.width_mm, component.aspect_percent,
                        component.rim_inches))
            oracle.call(0x52b950, (position,), this_pointer=owner,
                        cleanup=b'', instruction_limit=1_000_000)
            status = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            observed = tuple(bytes(cpu.mem_read(address, len(image)))
                              for address, image in zip(model_addresses, source_models))
            if status != int(expected.prepared) or observed != expected.models:
                raise AssertionError((vehicle_id, key, chosen, status,
                    expected.prepared, [next((i for i, (a, b) in enumerate(zip(x, y))
                        if a != b), None) for x, y in zip(observed, expected.models)]))
            reports.append((vehicle_id, key))
    return dict(cases=len(reports), max_error=0, original_entry='0x52b950',
        scope='stock tire and rim FCE pairs with catalogue dimensions for all four positions on vehicles 101-108; full images and return status compared')


def tire_image(rng, name=b':PHwheel', *, extent=(.4,.2,.3), origin=None):
    count = 4
    out = bytearray(0x2038 + count*36)
    struct.pack_into('<4I', out, 0, 0x101015, 0, 0, count)
    struct.pack_into('<I', out, 0x14, 0)
    struct.pack_into('<I', out, 0x34, count*12)
    struct.pack_into('<I', out, 0x2c, count*24)
    struct.pack_into('<I', out, 0x11c, 1)
    if origin is None:
        origin = (rng.uniform(-.8,.8), rng.uniform(-.5,.5), rng.uniform(-.5,.5))
    struct.pack_into('<3f', out, 0x120, *origin)
    struct.pack_into('<II', out, 0x420, 0, 0)
    struct.pack_into('<II', out, 0x520, count, 0)
    out[0xe28:0xe28+len(name)] = name
    x,y,z=extent
    points = ((-x,-y,-z),(x,-y,-z),(-x,y,z),(x,y,z))
    for i, point in enumerate(points):
        for stream, scale in enumerate((1., 2., 3.)):
            struct.pack_into('<3f', out, 0x2038+stream*count*12+i*12,
                             *(value*scale for value in point))
    return out


def verify_tire_preparation(executable, cases=128, position=1):
    if not 1 <= cases <= 4096:
        raise ValueError('case count must be from 1 to 4096')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    memory, owner, node, model = 0x74000000, 0x74001000, 0x74020000, 0x74010000
    cpu.mem_map(memory, 0x100000)
    rng = random.Random(0x52b950)
    for case in range(cases):
        source = tire_image(rng)
        width = rng.uniform(120., 360.)
        aspect = rng.uniform(35., 95.)
        rim = rng.uniform(12., 24.)
        component = TireModelComponent(0x1adb1, 1, 0, width, aspect, rim)
        group = PreparedModelGroup((bytes(source),), (0,), ())
        component = TireModelComponent(component.class_id, position, component.model,
            component.width_mm, component.aspect_percent, component.rim_inches)
        python_result = prepare_tire_models(group.models, (component,), position)
        cpu.mem_write(owner, bytes(0x400))
        cpu.mem_write(node, bytes(0x33c))
        cpu.mem_write(node, struct.pack('<II', 0, model))
        cpu.mem_write(node+0x18, struct.pack('<I', position))
        cpu.mem_write(node+0x14, struct.pack('<I', position))
        cpu.mem_write(node+0x3c, struct.pack('<3f', width, aspect, rim))
        cpu.mem_write(node+0x338, struct.pack('<I', 0x1adb1))
        cpu.mem_write(owner+0x19c, struct.pack('<I', node))
        cpu.mem_write(model, bytes(source))
        oracle.call(0x52b950, (position,), this_pointer=owner, cleanup=b'',
                    instruction_limit=1_000_000)
        status = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        observed = bytes(cpu.mem_read(model, len(source)))
        if status != int(python_result.prepared):
            raise AssertionError((case, 'return mismatch', status, python_result.prepared))
        if observed != python_result.models[0]:
            offsets = [i for i, (left, right) in enumerate(zip(observed,
                        python_result.models[0])) if left != right]
            raise AssertionError((case, 'FCE mismatch', width, aspect, rim,
                python_result.radius_m, python_result.width_m, python_result.size_scales,
                offsets[:16], [(offset, struct.unpack_from('<f', observed, offset)[0],
                    struct.unpack_from('<f', python_result.models[0], offset)[0])
                    for offset in offsets[:8] if offset % 4 == 0]))
    return dict(cases=cases, max_error=0, original_entry='0x52b950',
        scope='single tire component and model; full FCE image and return status compared, all three geometry streams exercised')


def verify_suspension_preparation(executable, cases=128):
    if not 1 <= cases <= 4096:
        raise ValueError('case count must be from 1 to 4096')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    memory, owner, nodes = 0x74000000, 0x74001000, 0x74020000
    model_addresses = (0x74010000, 0x74018000)
    cpu.mem_map(memory, 0x100000)
    rng = random.Random(0x52b7c0)
    for case in range(cases):
        tire = tire_image(rng, b':PHtire', extent=(.3,.2,.3),
            origin=(rng.choice((-.71,.71)),rng.uniform(-1,1),rng.uniform(-1,1)))
        suspension = tire_image(rng, b':PHrearsusp',
            extent=(rng.uniform(.08,.5),.15,.2), origin=(.2,.3,.4))
        selector = rng.choice((3,4))
        components = (TireModelComponent(0x1adb1, selector, 0),
                      TireModelComponent(0x3e9, 0, 1))
        expected = prepare_rear_suspension_model((bytes(tire),bytes(suspension)),components)
        cpu.mem_write(owner,bytes(0x400))
        for index,(model,component) in enumerate(zip(model_addresses,components)):
            address=nodes+index*0x400
            cpu.mem_write(address,bytes(0x33c))
            cpu.mem_write(address,struct.pack('<II',
                nodes+(index+1)*0x400 if index==0 else 0,model))
            cpu.mem_write(address+0x18,struct.pack('<I',component.position))
            cpu.mem_write(address+0x338,struct.pack('<I',component.class_id))
            cpu.mem_write(model,bytes((tire,suspension)[index]))
        cpu.mem_write(owner+0x19c,struct.pack('<I',nodes))
        oracle.call(0x52b7c0,(),this_pointer=owner,cleanup=b'',
                    instruction_limit=1_000_000)
        status=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        observed=tuple(bytes(cpu.mem_read(address,len(source))) for address,source in
                       zip(model_addresses,(tire,suspension)))
        if status!=int(expected.prepared):
            raise AssertionError((case,'return mismatch',status,expected.prepared))
        if observed!=expected.models:
            raise AssertionError((case,'FCE image mismatch'))
    return dict(cases=cases,max_error=0,original_entry='0x52b7c0',
        scope='single wheel model plus rear-suspension model, fallback position 3/4; full FCE images and return status compared')


def verify_integrated_preparation(executable, cases=128):
    """Compare the composed tire/suspension/centering path with 0x52be40."""
    if not 1 <= cases <= 4096:
        raise ValueError('case count must be from 1 to 4096')
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    memory, owner, nodes = 0x74000000, 0x74001000, 0x74040000
    model_addresses = (0x74010000, 0x74018000, 0x74028000)
    selected_nodes = 0x74050000
    output = oracle.inputs
    cpu.mem_map(memory, 0x100000)
    rng = random.Random(0x52be40_52b950_52b7c0)
    for case in range(cases):
        body = model_fixture(rng, tuple(rng.uniform(-2, 2) for _ in range(3)))
        tire = tire_image(rng, b':PHtire', extent=(.3,.2,.3),
            origin=(rng.choice((-.71,.71)), rng.uniform(-.5,.5), rng.uniform(-.5,.5)))
        suspension = tire_image(rng, b':PHrearsusp',
            extent=(rng.uniform(.08,.5),.15,.2), origin=(.2,.3,.4))
        width, aspect, rim = rng.uniform(180,340), rng.uniform(40,85), rng.uniform(13,22)
        components = (TireModelComponent(0, 0, 0),
            TireModelComponent(0x1adb1, 3, 1, width, aspect, rim),
            TireModelComponent(0x3e9, 0, 2))
        selected = (SelectedPart(0,0), SelectedPart(1,0), SelectedPart(2,0))
        group = PreparedModelGroup((bytes(body),bytes(tire),bytes(suspension)),
            (0,1,2), selected, owner_flags=0x40)
        expected = prepare_vehicle_model_group(group,components)
        for index, (address, source, component) in enumerate(zip(
                model_addresses, group.models, components)):
            cpu.mem_write(address, source)
            node = nodes+index*0x400
            cpu.mem_write(node, struct.pack('<II',
                nodes+(index+1)*0x400 if index+1<len(components) else 0, address))
            cpu.mem_write(node+0x18, struct.pack('<I', component.position))
            cpu.mem_write(node+0x14, struct.pack('<I', component.position))
            cpu.mem_write(node+0x338, struct.pack('<I', component.class_id))
            if component.class_id == 0x1adb1:
                cpu.mem_write(node+0x3c, struct.pack('<3f', width, aspect, rim))
            selected_node=selected_nodes+index*0x400
            cpu.mem_write(selected_node, struct.pack('<II',
                selected_nodes+(index+1)*0x400 if index+1<len(components) else 0, address))
            cpu.mem_write(selected_node+0x0c, struct.pack('<h',0))
            cpu.mem_write(selected_node+0x10, struct.pack('<I',0))
            cpu.mem_write(selected_node+0x14, struct.pack('<I',0))
        cpu.mem_write(owner+0x19c, struct.pack('<I',nodes))
        cpu.mem_write(owner+0x21c, struct.pack('<I',selected_nodes))
        cpu.mem_write(owner+0x22c, struct.pack('<I',0x40))
        if case == 0:
            oracle.call(0x52b950,(3,),this_pointer=owner,cleanup=b'',
                        instruction_limit=1_000_000)
            staged_tire=tuple(bytes(cpu.mem_read(address,len(source))) for address,source
                              in zip(model_addresses,group.models))
            wanted_tire=prepare_tire_models(group.models,components,3).models
            if staged_tire != wanted_tire:
                raise AssertionError(('integrated tire stage mismatch',
                    [i for i,(a,b) in enumerate(zip(staged_tire[1],wanted_tire[1]))
                     if a!=b][:16]))
            oracle.call(0x52b7c0,(),this_pointer=owner,cleanup=b'',
                        instruction_limit=1_000_000)
            staged_suspension=tuple(bytes(cpu.mem_read(address,len(source))) for address,source
                                    in zip(model_addresses,group.models))
            wanted_suspension=prepare_rear_suspension_model(wanted_tire,components).models
            if staged_suspension != wanted_suspension:
                raise AssertionError(('integrated suspension stage mismatch',
                    [(index,[i for i,(a,b) in enumerate(zip(actual,wanted))
                             if a!=b][:16])
                     for index,(actual,wanted) in enumerate(zip(staged_suspension,
                         wanted_suspension)) if actual!=wanted]))
            for address,source in zip(model_addresses,group.models):
                cpu.mem_write(address,source)
        cpu.mem_write(output, bytes(12))
        try:
            oracle.call(0x52be40, (output,), this_pointer=owner, cleanup=b'',
                        instruction_limit=1_000_000)
        except Exception as error:
            eip=cpu.reg_read(reg.UC_X86_REG_EIP)
            raise RuntimeError(f'integrated original execution fault at 0x{eip:08x} in case {case}') from error
        observed=tuple(bytes(cpu.mem_read(address,len(source))) for address,source in
                       zip(model_addresses,group.models))
        extents=bytes(cpu.mem_read(output,12))
        if observed != expected.result.group.models:
            mismatches=[]
            for index,(actual,wanted) in enumerate(zip(observed,
                    expected.result.group.models)):
                offsets=[i for i,(left,right) in enumerate(zip(actual,wanted))
                         if left!=right]
                if offsets:
                    mismatches.append((index,offsets[:12],len(offsets),
                        struct.unpack_from('<3f',actual,0x120),
                        struct.unpack_from('<3f',wanted,0x120)))
            raise AssertionError((case,'integrated image mismatch',mismatches,
                struct.unpack('<3f',bytes(cpu.mem_read(output,12))),
                expected.result.half_extents))
        if extents != struct.pack('<3f',*expected.result.half_extents):
            raise AssertionError((case,'integrated extent mismatch',
                struct.unpack('<3f',extents),expected.result.half_extents))
    return dict(cases=cases,max_error=0,original_entry='0x52be40',
        scope='full original call with three aliased-list nodes and separate body/tire/rear-suspension FCE images; compares every image byte and published extents; synthetic graph only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--tire-cases', type=int, default=0,
                        help='also compare 0x52b950 for this many single-tire cases')
    parser.add_argument('--tire-position', type=int, default=1,
                        help='wheel position for the optional 0x52b950 comparison (default 1)')
    parser.add_argument('--suspension-cases',type=int,default=0,
                        help='also compare 0x52b7c0 for these rear-suspension cases')
    parser.add_argument('--game', type=Path,
                        help='also compare unique stock body FCEs from this installed game Data root')
    parser.add_argument('--stock-pipeline', action='store_true',
                        help='compare installed body/tire/suspension FCE images for stock vehicles 101-108; requires --game')
    parser.add_argument('--stock-body-collector', action='store_true',
                        help='connect stock body flags/collector records to original 0x52be40; requires --game')
    parser.add_argument('--stock-wheels', action='store_true',
                        help='compare stock tire+rim preparation at all four positions on vehicles 101-108; requires --game')
    parser.add_argument('--integrated-cases', type=int, default=0,
                        help='compare the composed tire/suspension/centering translation against full original 0x52be40 calls')
    args = parser.parse_args()
    result = dict(model_group=verify(args.executable, args.cases))
    if args.tire_cases:
        result['tire_preparation'] = verify_tire_preparation(args.executable,
            args.tire_cases,args.tire_position)
    if args.suspension_cases:
        result['suspension_preparation'] = verify_suspension_preparation(
            args.executable,args.suspension_cases)
    if args.game:
        result['stock_bodies'] = verify_stock_bodies(args.executable,args.game)
        if args.stock_pipeline:
            result['stock_vehicle_pipeline'] = verify_stock_vehicle_pipeline(
                args.executable,args.game)
        if args.stock_body_collector:
            result['stock_body_collector'] = verify_stock_body_collector(
                args.executable,args.game)
        if args.stock_wheels:
            result['stock_wheels'] = verify_stock_wheel_preparation(
                args.executable,args.game)
    elif args.stock_pipeline or args.stock_wheels:
        parser.error('--stock-pipeline/--stock-wheels requires --game')
    if args.integrated_cases:
        result['integrated_preparation'] = verify_integrated_preparation(
            args.executable,args.integrated_cases)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
