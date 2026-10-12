"""Stock assembly preview using recovered marker placement and X reflection.

Wheel dimension scaling, suspension stance and nested engine assemblies are still
unresolved. This preserves natural component mesh dimensions until corroborated.
"""
from dataclasses import replace
from .assembly import select_body, stock_body_flags
from .fce import Model


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


def stock_scene(assets, body_path, vehicle, skin=None):
    body = assets.load_vehicle(body_path)
    flags = stock_body_flags(body, vehicle.parts)
    selected = select_body(body, flags)
    parts = list(selected.parts)
    textures = texture_slots(body, assets.load_textures(body_path, skin))
    notes = ['Tire dimension scaling and suspension stance remain unresolved.',
             'Nested engine assemblies are not yet placed.']
    loaded = {}

    def component(kind, attachment, group):
        stock = next((p for p in vehicle.parts if p.abstract_type_id == kind and
                      (attachment is None or p.attachment_id in attachment)), None)
        if stock is None or not stock.filename or stock.filename.startswith('.'):
            return None
        path = assets.paths.get(('data/models/'+stock.filename+'.viv').casefold())
        if path is None:
            notes.append(f'Missing component archive: {stock.filename}')
            return None
        if path not in loaded:
            model = assets.load_vehicle(path)
            page = len(textures)
            images = assets.load_textures(path)
            # Reserve every local page so it cannot alias another component.
            textures.extend(texture_slots(model, images))
            loaded[path] = (model, page)
        model, page = loaded[path]
        match = next((p for p in model.parts if p.name == ':PH'+group), None)
        return (match, page) if match is not None else None

    wheel_keys = {'LF': (1, 10), 'RF': (2, 10), 'LR': (3, 11), 'RR': (4, 11)}
    for marker in body.parts:
        if marker.name.startswith(':PP') and marker.name[3:-5] in wheel_keys and marker.name.endswith('wheel'):
            key = marker.name[3:-5]
            side, axle = wheel_keys[key]
            for kind, group in ((110001, 'tire'), (100001, 'hubcap')):
                child = component(kind, (side, axle), group)
                if child:
                    part, page = child
                    parts.append(place_part(part, marker.origin, key.startswith('R'), page,
                                            f'{key}:{group}'))
        elif marker.name == ':PPengine':
            child = component(160001, None, 'engine')
            if child:
                part, page = child
                parts.append(place_part(part, marker.origin, False, page, 'engine'))
    return Model(tuple(parts), body.version, body.warnings), tuple(textures), flags, tuple(notes)
