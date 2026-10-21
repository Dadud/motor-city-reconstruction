"""Stock geometry preview with recovered body, wheel and engine attachment rules.

Other accessory classes and full owner-model construction remain incomplete.
"""
from dataclasses import dataclass, replace
from types import SimpleNamespace
from .assembly import select_body, stock_body_flags
from .fce import Model, decode as decode_fce
from .model_group_centering import (TireModelComponent,
    prepare_rear_suspension_model, prepare_tire_models)
from .render_list import RenderRecord
from .tire_response import f32

# Component-class prefixes read from the original 0x8957a0 pointer table.
# Entries include the four wheel corners and generic left/right/accessory
# classes used by attachment model names.
_MODEL_CLASS_PREFIXES = ('LF', 'RF', 'LR', 'RR', 'L', 'R', 'A', 'B', 'C', 'F')
_MODEL_CLASS_BY_INDEX = ('', 'LF', 'RF', 'LR', 'RR', 'L', 'R', 'A', 'B', 'C', 'F', 'R')
DRIVER_MODEL_BY_VARIANT = (
    'driver18', 'driver22', 'driver20', 'driver27', 'driver1', 'driver2',
    'driver15', 'driver23', 'driver16', 'driver14', 'driver33', 'driver28',
    'driver3', 'driver4', 'driver19', 'driver26', 'driver5', 'driver6',
    'driver7', 'driver8', 'driver21', 'driver24', 'driver17', 'driver25',
    'driver9', 'driver10', 'driver29', 'driver30', 'driver31', 'driver32',
    'driver11', 'driver12', 'driver13',
)
_NESTED_ENGINE_COMPONENTS = {
    'valve': 1500001, 'manifold': 320001,
    'carb': 330001, 'aircleaner': 340001,
}


@dataclass(frozen=True)
class ComponentModelNode:
    """One resolved node from the native component-model linked list."""
    class_index: int
    model: Model
    model_handle: int
    component_type: int = 0


@dataclass(frozen=True)
class ComponentNodeSelection:
    node_index: int
    part_index: int
    record: RenderRecord


@dataclass(frozen=True)
class ComponentRenderEntry:
    """One generic marker selected while traversing a component FCE graph."""
    marker_path: tuple[str, ...]
    node_index: int
    part_index: int
    record: RenderRecord


@dataclass(frozen=True)
class ComponentRenderGraph:
    """Generic render records and mutated model images from one graph walk."""
    entries: tuple[ComponentRenderEntry, ...]
    models: tuple[Model, ...]


def collect_component_render_graph(root_model, nodes, lod=0, owner_flags=0):
    """Translate generic recursive :PP selection in `0x52df00`.

    `nodes` are supplied in native linked-list order and retain their native
    class-table index and model handle. Generic markers recurse at LOD zero;
    the observed driver, rear-suspension, and wheel special markers are also
    emitted where implemented.
    At LOD zero, component FCE mutations are carried forward before traversing
    nested markers, matching the native in-place recursive walk.
    """
    if not isinstance(root_model, Model):
        raise TypeError('root_model must be a decoded FCE Model')
    if type(lod) is not int or lod < 0:
        raise ValueError('LOD must be a nonnegative integer')
    if type(owner_flags) is not int or not 0 <= owner_flags <= 0xffffffff:
        raise ValueError('owner flags must be an unsigned 32-bit integer')
    effective_flags = owner_flags & (0xfffeffff if lod > 2 else 0xffffffff)
    nodes = tuple(nodes)
    for node in nodes:
        if not isinstance(node, ComponentModelNode):
            raise TypeError('nodes must contain ComponentModelNode instances')
    current_models = [node.model for node in nodes]
    entries = []
    special_suffixes = frozenset(('driver', 'driverhead', 'rearsusp', 'wheel'))
    active_edges = set()

    def visit(parent_model, parent_path):
        for marker in parent_model.parts:
            if not marker.name.startswith(':PP'):
                continue
            class_prefix, suffix = split_component_marker(marker.name)
            if class_prefix is None or not suffix:
                continue
            if suffix == 'engine' and not effective_flags & 0x10000:
                continue
            if suffix == 'driverhead':
                continue
            if suffix == 'driver' and class_prefix == '':
                driver_index = next((index for index, node in enumerate(nodes)
                                     if node.component_type == 0x80e9), None)
                if driver_index is None:
                    continue
                node = replace(nodes[driver_index], model=current_models[driver_index])
                driver = select_component_part(node.model, 'driver', min(lod, 3))
                head = select_component_part(node.model, 'driverhead', min(lod, 3))
                if driver is None:
                    continue
                driver_index_in_model = next(i for i, part in enumerate(node.model.parts)
                                             if part is driver)
                driver_origin = tuple(marker.origin)
                placed_driver = place_part(driver, driver_origin, name='driver')
                words = [0] * 9
                words[1], words[3] = node.model_handle, driver_index_in_model
                words[4], words[5] = (1 << min(lod, 3)) | 0x80, 0x11
                model_parts = list(node.model.parts)
                model_parts[driver_index_in_model] = placed_driver
                path = parent_path + (marker.name,)
                entries.append(ComponentRenderEntry(path, driver_index,
                    driver_index_in_model, RenderRecord(tuple(words))))
                if head is not None:
                    head_index = next(i for i, part in enumerate(node.model.parts)
                                      if part is head)
                    head_origin = tuple(f32(f32(f32(h) - f32(d)) + f32(m))
                                        for h, d, m in zip(head.origin, driver.origin,
                                                           marker.origin))
                    placed_head = place_part(head, head_origin, name='driverhead')
                    model_parts[head_index] = placed_head
                    words = [0] * 9
                    words[1], words[3] = node.model_handle, head_index
                    words[4], words[5] = (1 << min(lod, 3)) | 0x80, 0x10
                    entries.append(ComponentRenderEntry(path, driver_index,
                        head_index, RenderRecord(tuple(words))))
                current_models[driver_index] = Model(tuple(model_parts), node.model.version,
                                                     node.model.warnings)
                continue
            if suffix == 'rearsusp' and class_prefix == '':
                lookup_nodes = tuple(replace(node, model=current_models[index])
                                     for index, node in enumerate(nodes))
                selection = select_component_node(lookup_nodes, '', 'rearsusp', lod)
                if selection is None:
                    continue
                node = lookup_nodes[selection.node_index]
                result = attach_rear_suspension(marker, node.model, lod,
                                                node.model_handle)
                if result is None:
                    continue
                attached, record = result
                parts = list(node.model.parts)
                parts[selection.part_index] = attached
                current_models[selection.node_index] = Model(
                    tuple(parts), node.model.version, node.model.warnings)
                path = parent_path + (marker.name,)
                entries.append(ComponentRenderEntry(path, selection.node_index,
                    selection.part_index, record))
                continue
            if suffix == 'wheel' and class_prefix in ('LF', 'RF', 'LR', 'RR'):
                tire_type, hubcap_type = {
                    'LF': (8, 4), 'RF': (9, 5),
                    'LR': (11, 7), 'RR': (10, 6),
                }[class_prefix]
                path = parent_path + (marker.name,)
                for part_suffix, mesh_type, tire_mesh in (
                        ('tire', tire_type, True),
                        ('hubcap', hubcap_type, False)):
                    lookup_nodes = tuple(replace(node, model=current_models[index])
                                         for index, node in enumerate(nodes))
                    selection = select_component_node(lookup_nodes, class_prefix,
                                                      part_suffix, lod)
                    if selection is None:
                        continue
                    node = lookup_nodes[selection.node_index]
                    selected = node.model.parts[selection.part_index]
                    placed = place_part(selected, marker.origin,
                                         name=part_suffix)
                    parts = list(node.model.parts)
                    parts[selection.part_index] = placed
                    current_models[selection.node_index] = Model(
                        tuple(parts), node.model.version, node.model.warnings)
                    words = list(selection.record.words)
                    if tire_mesh:
                        words[4] |= 0x80
                    words[5] = mesh_type
                    entries.append(ComponentRenderEntry(path,
                        selection.node_index, selection.part_index,
                        RenderRecord(tuple(words))))
                continue
            if suffix in special_suffixes:
                continue
            lookup_nodes = tuple(replace(node, model=current_models[index])
                                 for index, node in enumerate(nodes))
            selection = select_component_node(lookup_nodes, class_prefix, suffix, lod)
            if selection is None:
                continue
            node_index = selection.node_index
            marker_key = (node_index, marker.name)
            if marker_key in active_edges:
                raise ValueError('cyclic generic component marker graph')
            active_edges.add(marker_key)
            node = lookup_nodes[node_index]
            attached = attach_component_marker(marker, node.model, lod,
                                                node.model_handle)
            if attached is None:
                active_edges.remove(marker_key)
                continue
            transformed, part_index, record = attached
            current_models[node_index] = transformed
            path = parent_path + (marker.name,)
            entries.append(ComponentRenderEntry(path, node_index, part_index, record))
            if lod == 0:
                visit(transformed, path)
            active_edges.remove(marker_key)

    visit(root_model, ())
    return ComponentRenderGraph(tuple(entries), tuple(current_models))


def split_component_marker(marker):
    """Split a :PP marker into its observed component class and suffix."""
    if not marker.startswith(':PP'):
        return None, None
    text = marker[3:]
    for prefix in sorted(_MODEL_CLASS_PREFIXES, key=len, reverse=True):
        if text.startswith(prefix):
            return prefix, text[len(prefix):]
    return '', text


def _marker_component_prefix(marker, attachment_id):
    """Return a wheel-corner prefix for the native tire component class."""
    if attachment_id != 0x1adb1:
        return None
    prefix, suffix = split_component_marker(marker)
    return prefix if prefix in ('LF', 'RF', 'LR', 'RR') and suffix == 'wheel' else None


def select_component_part(model, suffix, maximum_option=0):
    """Select an exact option+suffix, reproducing 0x52e670's descending scan."""
    if type(maximum_option) is not int:
        raise TypeError('component option must be an integer')
    maximum_option = min(maximum_option, 3)
    if maximum_option < 0:
        return None
    prefixes = (':PH', ':PM', ':PS', ':PT')
    for option in range(maximum_option, -1, -1):
        name = prefixes[option] + suffix
        match = next((part for part in model.parts if part.name == name), None)
        if match is not None:
            return match
    return None


def select_component_node(nodes, class_prefix, suffix, maximum_option=0):
    """Recover 0x52e670's LOD-major lookup through owner node-class slots."""
    if not isinstance(class_prefix, str) or '\0' in class_prefix:
        raise ValueError('component class prefix must be a NUL-free string')
    if not isinstance(suffix, str) or not suffix or '\0' in suffix:
        raise ValueError('component suffix must be nonempty and NUL-free')
    if type(maximum_option) is not int or maximum_option < 0:
        raise ValueError('component option must be a nonnegative integer')
    requested = min(maximum_option, 3)
    nodes = tuple(nodes)
    for node in nodes:
        if not isinstance(node, ComponentModelNode):
            raise TypeError('nodes must contain ComponentModelNode instances')
        if type(node.class_index) is not int or not 0 <= node.class_index < len(_MODEL_CLASS_BY_INDEX):
            raise ValueError('component class index is outside the native pointer table')
        if type(node.model_handle) is not int or not 0 <= node.model_handle <= 0xffffffff:
            raise ValueError('component model handle must be an unsigned 32-bit integer')
    prefixes = (':PH', ':PM', ':PS', ':PT')
    for option in range(requested, -1, -1):
        name = prefixes[option] + suffix
        for node_index, node in enumerate(nodes):
            if _MODEL_CLASS_BY_INDEX[node.class_index] != class_prefix:
                continue
            part_index = next((index for index, part in enumerate(node.model.parts)
                               if part.name == name), None)
            if part_index is None:
                continue
            words = [0] * 9
            words[1] = node.model_handle
            words[3] = part_index & 0xffff
            words[4] = (1 << requested) | (0x40 if class_prefix.startswith('R') else 0)
            return ComponentNodeSelection(node_index, part_index,
                                          RenderRecord(tuple(words)))
    return None


def attach_component_from_nodes(marker, nodes, lod=0):
    """Select the native class/model node, then apply its generic marker transform."""
    class_prefix, suffix = split_component_marker(marker.name)
    if class_prefix is None or not suffix:
        raise ValueError('generic attachment requires a named :PP component marker')
    selection = select_component_node(nodes, class_prefix, suffix, lod)
    if selection is None:
        return None
    node = tuple(nodes)[selection.node_index]
    attached = attach_component_marker(marker, node.model, lod, node.model_handle)
    if attached is None:
        return None
    model, part_index, record = attached
    return model, selection.node_index, part_index, record


def texture_slots(model, images):
    count = max((t.texture_page+1 for p in model.parts for t in p.triangles), default=0)
    count = max(count, len(images))
    if count > 256:
        raise ValueError('component texture page count exceeds budget')
    return list(images) + [None] * (count-len(images))


def place_part(part, origin, mirror=False, page_offset=0, name=None):
    def reflect(vector):
        return (-vector[0], vector[1], vector[2]) if mirror else vector
    return replace(part, name=name or part.name, origin=tuple(origin),
        vertices=tuple(reflect(v) for v in part.vertices),
        normals=tuple(reflect(n) for n in part.normals),
        triangles=tuple(replace(t, texture_page=t.texture_page+page_offset) for t in part.triangles))


def attach_rear_suspension(marker, component_model, lod=0, model_handle=0,
                           page_offset=0):
    """Attach the special `:PPrearsusp` branch recovered from 0x52df00.

    Returns the marker-positioned FCE part and its portable nine-word record,
    or ``None`` when the selected component lacks a matching LOD part.
    ``model_handle`` stands in for the native model pointer in word 1.
    """
    if marker.name != ':PPrearsusp':
        raise ValueError('rear suspension attachment requires the :PPrearsusp marker')
    if type(lod) is not int or lod < 0:
        raise ValueError('LOD must be a nonnegative integer')
    if type(model_handle) is not int or not 0 <= model_handle <= 0xffffffff:
        raise ValueError('model handle must be an unsigned 32-bit integer')
    selected = select_component_part(component_model, 'rearsusp', min(lod, 3))
    if selected is None:
        return None
    part_index = next(index for index, part in enumerate(component_model.parts)
                      if part is selected)
    record_words = [0] * 9
    record_words[1] = model_handle
    record_words[3] = part_index & 0xffff
    record_words[4] = (1 << min(lod, 3)) | 0x80
    record_words[5] = 0x0f
    return (place_part(selected, marker.origin, page_offset=page_offset,
                       name='rearsusp'), RenderRecord(tuple(record_words)))


def attach_component_marker(marker, component_model, lod=0, model_handle=0):
    """Translate the ordinary :PP component branch of 0x52df00.

    The caller supplies the owner node selected by the marker's class prefix.
    This handles exact LOD part selection, right-side mirroring, origin rebasing,
    and vertex-stream transformation when the native LOD argument is zero.
    Recursive child selection remains a separate step.
    """
    class_prefix, suffix = split_component_marker(marker.name)
    if class_prefix is None or not suffix:
        raise ValueError('generic attachment requires a named :PP component marker')
    if type(lod) is not int or lod < 0:
        raise ValueError('LOD must be a nonnegative integer')
    if type(model_handle) is not int or not 0 <= model_handle <= 0xffffffff:
        raise ValueError('model handle must be an unsigned 32-bit integer')
    requested = min(lod, 3)
    selected = select_component_part(component_model, suffix, requested)
    if selected is None:
        return None
    selected_index = next(index for index, part in enumerate(component_model.parts)
                          if part is selected)
    anchor = selected.origin
    mirrored = class_prefix.startswith('R')

    def rebase(vector):
        result = []
        for axis, (value, origin, target) in enumerate(zip(vector, anchor, marker.origin)):
            delta = f32(value-origin)
            if mirrored and axis == 0:
                delta = f32(-delta)
            result.append(f32(delta+target))
        return tuple(result)

    transformed_parts = []
    for index, part in enumerate(component_model.parts):
        origin = part.origin
        vertices = part.vertices
        if lod == 0:
            if part.name.startswith(':PP'):
                origin = rebase(origin)
            vertices = tuple(rebase(vertex) for vertex in vertices)
        if index == selected_index:
            origin = tuple(marker.origin)
        transformed_parts.append(replace(part, origin=origin, vertices=vertices))
    words = [0] * 9
    words[1] = model_handle
    words[3] = selected_index & 0xffff
    words[4] = (1 << requested) | (0x40 if mirrored else 0)
    words[5] = 0
    transformed_model = Model(tuple(transformed_parts), component_model.version,
                              component_model.warnings)
    return transformed_model, selected_index, RenderRecord(tuple(words))


def stock_scene(assets, body_path, vehicle, skin=None, tire_dimensions=None,
                driver_variant=0):
    if type(driver_variant) is not int or not 0 <= driver_variant < len(DRIVER_MODEL_BY_VARIANT):
        raise ValueError('driver variant must be in [0, 32]')
    body = assets.load_vehicle(body_path)
    flags = stock_body_flags(body, vehicle.parts)
    selected = select_body(body, flags)
    parts = list(selected.parts)
    textures = texture_slots(body, assets.load_textures(body_path, skin))
    notes = []
    if tire_dimensions is None:
        notes.append('Tire dimensions were not supplied; tire and rear suspension geometry remain unscaled.')
    loaded = {}

    def load_component(stock, group, prepared_image=None):
        if not stock.filename or stock.filename.startswith('.'):
            return None
        path = assets.paths.get(('data/models/'+stock.filename+'.viv').casefold())
        if path is None:
            notes.append(f'Missing component archive: {stock.filename}')
            return None
        if path not in loaded:
            component_model = assets.load_vehicle(path)
            page = len(textures)
            textures.extend(texture_slots(component_model, assets.load_textures(path)))
            loaded[path] = (component_model, page)
        component_model, page = loaded[path]
        if prepared_image is not None:
            component_model = decode_fce(prepared_image)
        return select_component_part(component_model, group), page

    prepared_rear_tire = None
    wheel_positions = {'LF': 1, 'RF': 2, 'LR': 3, 'RR': 4}
    for marker in body.parts:
        prefix = _marker_component_prefix(marker.name, 0x1adb1)
        if prefix is None or not marker.name.endswith('wheel'):
            continue
        side, axle = {'LF': (1, 10), 'RF': (2, 10),
                      'LR': (3, 11), 'RR': (4, 11)}[prefix]
        position = wheel_positions[prefix]
        selected_wheels = []
        for kind, group, node_class in ((110001, 'tire', 0x1adb1),
                                        (100001, 'hubcap', 0x186a1)):
            stock = next((p for p in vehicle.parts
                if p.abstract_type_id == kind and p.attachment_id == side), None)
            if stock is None:
                stock = next((p for p in vehicle.parts
                    if p.abstract_type_id == kind and p.attachment_id == axle), None)
            if stock is not None:
                selected_wheels.append((kind, group, node_class, stock))

        prepared_images = {}
        if (tire_dimensions is not None and selected_wheels and
                selected_wheels[0][0] == 110001):
            source_images, components = [], []
            for kind, group, node_class, stock in selected_wheels:
                path = assets.paths.get(('data/models/'+stock.filename+'.viv').casefold())
                if path is None:
                    continue
                model_index = len(source_images)
                source_images.append(assets.load_vehicle_bytes(path))
                if kind == 110001:
                    size = tire_dimensions[prefix]
                    components.append(TireModelComponent(node_class, position,
                        model_index, size.width_mm, size.aspect_percent,
                        size.rim_inches))
                else:
                    components.append(TireModelComponent(node_class, position,
                        model_index))
                prepared_images[kind] = model_index
            if source_images and any(c.class_id == 0x1adb1 for c in components):
                prepared = prepare_tire_models(source_images, components, position)
                if prepared.prepared:
                    prepared_images = {kind: prepared.models[index]
                                       for kind, index in prepared_images.items()}
                    if prefix == 'LR':
                        prepared_rear_tire = prepared.models[0]
                else:
                    prepared_images = {}
                    notes.append(f'Tire preparation did not match native geometry for {prefix}.')

        for kind, group, node_class, stock in selected_wheels:
            image = prepared_images.get(kind)
            if isinstance(image, int):
                image = None
            child = load_component(stock, group, image)
            if child is None:
                continue
            match, page = child
            if match is not None:
                parts.append(place_part(match, marker.origin, prefix.startswith('R'),
                                         page, f'{prefix}:{group}'))

    suspension_marker = next((p for p in body.parts if p.name == ':PPrearsusp'), None)
    suspension_stock = next((p for p in vehicle.parts if p.abstract_type_id == 1001), None)
    if suspension_marker is not None and suspension_stock is not None:
        suspension_image = None
        if prepared_rear_tire is not None:
            path = assets.paths.get(
                ('data/models/'+suspension_stock.filename+'.viv').casefold())
            if path is not None:
                original = assets.load_vehicle_bytes(path)
                prepared = prepare_rear_suspension_model(
                    (prepared_rear_tire, original),
                    (TireModelComponent(0x1adb1, 3, 0),
                     TireModelComponent(0x3e9, 0, 1)))
                if prepared.prepared:
                    suspension_image = prepared.models[1]
        child = load_component(suspension_stock, 'rearsusp', suspension_image)
        if child is not None and child[0] is not None:
            suspension_part, page = child
            parts.append(place_part(suspension_part, suspension_marker.origin,
                                    False, page, 'rearsusp'))
    engine_marker = next((p for p in body.parts if p.name == ':PPengine'), None)
    engine = next((p for p in vehicle.parts if p.abstract_type_id == 160001), None)
    if engine_marker is not None and engine is not None:
        child = load_component(engine, 'engine')
        if child is not None and child[0] is not None:
            _, page = child
            engine_path = assets.paths[('data/models/'+engine.filename+'.viv').casefold()]
            attachment = attach_component_from_nodes(engine_marker,
                (ComponentModelNode(0, loaded[engine_path][0], 0),))
            if attachment is None:
                notes.append('Selected engine model lacks a matching :PPengine component part.')
                attachment_model = None
            else:
                attachment_model, _, engine_index, _ = attachment
                engine_part = attachment_model.parts[engine_index]
                parts.append(place_part(engine_part, engine_part.origin, False,
                                         page, 'engine'))

            def nested(parent_model, chain, depth):
                if depth >= 6:
                    notes.append(f'Engine attachment depth limit reached at {chain}.')
                    return
                for marker_part in parent_model.parts:
                    if not marker_part.name.startswith(':PP'):
                        continue
                    _, suffix = split_component_marker(marker_part.name)
                    if suffix is None:
                        continue
                    kind = _NESTED_ENGINE_COMPONENTS.get(suffix.casefold())
                    if kind is None:
                        continue
                    stock = next((p for p in vehicle.parts
                                  if p.abstract_type_id == kind), None)
                    if stock is None:
                        notes.append(f'No stock component for nested engine marker {marker_part.name}.')
                        continue
                    nested_child = load_component(stock, suffix)
                    if nested_child is None or nested_child[0] is None:
                        continue
                    _, child_page = nested_child
                    loaded_model_path = assets.paths[
                        ('data/models/'+stock.filename+'.viv').casefold()]
                    child_model = loaded[loaded_model_path][0]
                    nested_attachment = attach_component_from_nodes(marker_part,
                        (ComponentModelNode(0, child_model, 0),))
                    if nested_attachment is None:
                        continue
                    attached_model, _, child_index, _ = nested_attachment
                    child_part = attached_model.parts[child_index]
                    child_origin = marker_part.origin
                    child_name = chain + ':' + suffix.casefold()
                    parts.append(place_part(child_part, child_origin, False,
                                             child_page, child_name))
                    nested(attached_model, child_name, depth+1)

            if attachment_model is not None:
                nested(attachment_model, 'engine', 0)
    elif engine_marker is not None:
        notes.append('No selected engine component is available for the :PPengine marker.')

    driver_marker = next((p for p in body.parts if p.name == ':PPdriver'), None)
    if driver_marker is not None:
        driver = SimpleNamespace(filename=DRIVER_MODEL_BY_VARIANT[driver_variant])
        child = load_component(driver, 'driver')
        if child is not None and child[0] is not None:
            driver_part, page = child
            driver_model_path = assets.paths[
                ('data/models/'+driver.filename+'.viv').casefold()]
            driver_model = loaded[driver_model_path][0]
            driver_part = select_component_part(driver_model, 'driver')
            head = select_component_part(driver_model, 'driverhead')
            parts.append(place_part(driver_part, driver_marker.origin, False,
                                    page, 'driver'))
            if head is not None and driver_part is not None:
                # 0x52df00 stores each intermediate float: head-driver, then
                # marker+offset. Preserve those float32 roundings instead of
                # doing both operations in Python's double precision.
                head_origin = tuple(f32(f32(head_value-driver_value)+marker_value)
                    for marker_value, head_value, driver_value in zip(
                        driver_marker.origin, head.origin, driver_part.origin))
                parts.append(place_part(head, head_origin, False, page, 'driverhead'))
    return Model(tuple(parts), body.version, body.warnings), tuple(textures), flags, tuple(notes)
