"""Body render-group selection recovered from mcity 0x52d710 / 0x52db70.

This selects visual body groups only, including reconstructed stock flags.
Named profiles are preview choices; attached components are not assembled here.
"""
from dataclasses import dataclass, replace
from .fce import Model
from .render_list import RenderRecord

LOD_PREFIXES = (':H', ':M', ':S', ':T')
# Common preview equipment plus a mutually exclusive roof style.
PREVIEW_BASE = 0x40000 | 1 | 0x800 | 0x100 | 0x200 | 0x1000 | 0x2000 | 0x4000 | 0x10000
PROFILES = {'standard': PREVIEW_BASE | 0x20, 'chopped': PREVIEW_BASE | 0x40,
            'convertible': PREVIEW_BASE | 0x80}

# Recovered flag/filename choices at mcity PE VA 0x895568. Order matters:
# a scoop selects the first option supported by the available body groups.
CONFIGURATION = (
    (31001, 0, (('.chopped', 0x40), ('.convert', 0x80), ('.vinyl', 0x20), ('', 0x20))),
    (34001, 10, (('', 0x1000),)), (34001, 11, (('', 0x2000),)),
    (23001, 0, (('', 0x4000),)), (35001, 0, (('', 0x800),)),
    (21001, 0, (('', 0x400),)), (29001, 0, (('', 0x8000),)),
    (40001, 0, (('.factory', 0x10), ('.large', 6), ('.large', 5),
                ('.large', 4), ('.small', 10), ('.small', 9),
                ('.small', 8), ('.hole', 2), ('', 1))),
    (17001, 0, (('', 0x20000),)),
)
AVAILABLE_GROUPS = (('hood', 1), ('hoodhole', 2), ('scooplarge', 4),
    ('scoopsmall', 8), ('scoopfact', 0x10), ('top', 0x20), ('topchop', 0x40),
    ('convertible', 0x80), ('rmirror', 0x100), ('lmirror', 0x200),
    ('skirt', 0x400), ('bumper', 0x800), ('ffender', 0x1000),
    ('rfender', 0x2000), ('boards', 0x4000), ('chin', 0x8000), ('cage', 0x20000))


@dataclass(frozen=True)
class BodyComponentNameNode:
    """Minimal class/name/attachment view of a native assembly-list node."""
    class_id: int
    name: str
    attachment_id: int = 0


def normalize_body_component_names(nodes):
    """Reproduce 0x52e880's bounded linked-node name rewrites.

    The first 40001 node is the scoop slot. A named 340333 blower forces its
    name to ``.hole``; otherwise a present 350001 scoop forces that rewrite
    only when the slot name is outside the three accepted factory scoop names.
    The first 1001 node is then renamed to the original static alias ``SUSP``.
    The function returns copied nodes and preserves owner-list order.
    """
    nodes = tuple(nodes)
    for node in nodes:
        if not isinstance(node, BodyComponentNameNode):
            raise TypeError('nodes must contain BodyComponentNameNode values')
        if type(node.class_id) is not int or not 0 <= node.class_id <= 0xffffffff:
            raise ValueError('component class must be an unsigned 32-bit integer')
        if type(node.attachment_id) is not int or not 0 <= node.attachment_id <= 0xffffffff:
            raise ValueError('component attachment must be an unsigned 32-bit integer')
        if not isinstance(node.name, str) or '\0' in node.name:
            raise ValueError('component name must be a NUL-free string')

    result = list(nodes)
    scoop_index = next((i for i, node in enumerate(nodes)
                        if node.class_id == 40001), None)
    if scoop_index is not None:
        blower = next((node for node in nodes if node.class_id == 340333), None)
        if blower is not None and blower.name:
            result[scoop_index] = replace(result[scoop_index], name='.hole')
        elif any(node.class_id == 350001 for node in nodes):
            if nodes[scoop_index].name not in ('.factory', '.large', '.small'):
                result[scoop_index] = replace(result[scoop_index], name='.hole')

    suspension_index = next((i for i, node in enumerate(nodes)
                             if node.class_id == 1001), None)
    if suspension_index is not None:
        result[suspension_index] = replace(result[suspension_index], name='SUSP')
    return tuple(result)


def stock_body_flags(model, stock_parts):
    """0x52e880's body visibility mask from model groups and stock identities.

    This does not use StockAssembly.ConfigDefault as a visibility switch.
    It expects the catalogue's resolved part filename, before VIV path expansion.
    The native routine's linked-node name mutations are not returned here.
    """
    names = {part.name for part in model.parts}
    available = 0x40000
    for group, bit in AVAILABLE_GROUPS:
        if ':H'+group in names:
            available |= bit
    installed = 0x40000 | (available & 0x300)  # Mirrors present by default.
    def class_id(part):
        return getattr(part, 'abstract_type_id', getattr(part, 'class_id', None))

    def part_name(part):
        return getattr(part, 'filename', getattr(part, 'name', '')) or ''

    blower = next((p for p in stock_parts if class_id(p) == 340333), None)
    scoop = next((p for p in stock_parts if class_id(p) == 350001), None)
    for kind, attachment, options in CONFIGURATION:
        part = next((p for p in stock_parts if class_id(p) == kind and
                     (not attachment or p.attachment_id == attachment)), None)
        if part is None:
            continue
        filename = part_name(part)
        if kind == 40001:
            if blower is not None and part_name(blower):
                filename = '.hole'
            elif scoop is not None and filename not in ('.factory', '.large', '.small'):
                filename = '.hole'
        for candidate, flags in options:
            if available & flags == flags and (not candidate or filename == candidate):
                installed |= flags
                break
    if not installed & 0x1d:
        available |= 0x10000
        installed |= 0x10000
    return available & installed


def body_groups(flags, interior=True):
    groups = ['body', 'headlight']
    if interior:
        groups += ['interior', 'dashlight', 'steer']
    if not flags & 0x40000:
        return tuple(groups)
    for bit, name in ((1, 'hood'), (2, 'hoodhole'), (4, 'scooplarge'),
                      (8, 'scoopsmall'), (0x10, 'scoopfact')):
        if flags & bit:
            groups.append(name)
    if flags & 0x20:
        groups += ['top', 'shield', 'swin']
    if flags & 0x80:
        groups += ['convertible', 'shield', 'swin']
    if flags & 0x40:
        groups += ['topchop', 'shieldchop', 'swinchop']
    if flags & 0x20000:
        groups.append('cagechop' if flags & 0x40 else 'cage')
    for bit, name in ((0x800, 'bumper'), (0x100, 'rmirror'), (0x200, 'lmirror'),
                      (0x400, 'skirt')):
        if flags & bit:
            groups.append(name)
    groups += ['wheelwell', 'ffender' if flags & 0x1000 else 'fenderlight']
    for bit, name in ((0x2000, 'rfender'), (0x4000, 'boards'),
                      (0x8000, 'chin'), (0x10000, 'firewall')):
        if flags & bit:
            groups.append(name)
    if not flags & (0x20 | 0x40 | 0x80):
        groups.append('shield')
    return tuple(dict.fromkeys(groups))


def select_body(model, flags, lod=0):
    if not 0 <= lod <= 3:
        raise ValueError('body LOD must be between 0 and 3')
    parts = []
    # The native selector tries the requested prefix, then lower indices.
    for group in body_groups(flags, interior=lod < 3):
        if group in ('dashlight', 'steer') and not any(p.name.endswith('interior') for p in parts):
            continue
        for level in range(lod, -1, -1):
            match = next((part for part in model.parts if part.name == LOD_PREFIXES[level]+group), None)
            if match is not None:
                parts.append(match)
                break
    return Model(tuple(parts), model.version, model.warnings)


def collect_render_group(models, group, lod, extra_flags=0, mesh_type=0):
    """Translate one 0x52db70 group lookup into a portable render record.

    LOD selection is the outer loop and linked-model order is the inner loop,
    matching the native search. ``model_index`` occupies the model-pointer
    slot as a stable portable handle; runtime integration can resolve it to an
    address when it owns the model graph.
    """
    if type(lod) is not int or lod < 0:
        raise ValueError('LOD must be a nonnegative integer')
    if not isinstance(group, str) or not group or '\0' in group:
        raise ValueError('group must be a nonempty NUL-free string')
    if type(extra_flags) is not int or not 0 <= extra_flags <= 0xffffffff:
        raise ValueError('extra flags must be an unsigned 32-bit integer')
    if type(mesh_type) is not int or not 0 <= mesh_type <= 0xffffffff:
        raise ValueError('mesh type must be an unsigned 32-bit integer')
    models = tuple(models)
    for level in range(min(lod, 3), -1, -1):
        name = LOD_PREFIXES[level] + group
        for model_index, model in enumerate(models):
            if not isinstance(model, Model):
                raise TypeError('models must contain decoded FCE Model instances')
            part_index = next((index for index, part in enumerate(model.parts)
                              if part.name == name), None)
            if part_index is None:
                continue
            words = [0] * 9
            words[1] = model_index
            words[3] = part_index
            # Native writes the requested LOD argument, even when it found a
            # lower fallback prefix; it does not write the matched level.
            words[4] = (1 << min(lod, 3)) | extra_flags
            words[5] = mesh_type
            return RenderRecord(tuple(words))
    return None


def collect_body_render_records(model, flags, lod, include_interior=True):
    """Run the ordered group calls made by 0x52d710 for one body FCE."""
    if type(flags) is not int or not 0 <= flags <= 0xffffffff:
        raise ValueError('body flags must be an unsigned 32-bit integer')
    if type(include_interior) is not bool:
        raise TypeError('include_interior must be bool')
    groups = [('body', 0, 1), ('headlight', 0, 2)]
    records = []
    for group, extra_flags, mesh_type in groups:
        record = collect_render_group((model,), group, lod, extra_flags, mesh_type)
        if record is not None:
            records.append(record)
    if include_interior:
        interior = collect_render_group((model,), 'interior', lod, 0x80, 0x14)
        if interior is not None:
            records.append(interior)
            for group, extra_flags, mesh_type in (
                    ('dashlight', 0x80, 0x13), ('steer', 0x180, 0x12)):
                record = collect_render_group((model,), group, lod,
                                              extra_flags, mesh_type)
                if record is not None:
                    records.append(record)
    if not flags & 0x40000:
        return tuple(records)

    selected = []
    def add(group, extra_flags=0, mesh_type=0):
        record = collect_render_group((model,), group, lod, extra_flags, mesh_type)
        if record is not None:
            selected.append(record)

    for bit, group in ((1, 'hood'), (2, 'hoodhole'), (4, 'scooplarge'),
                       (8, 'scoopsmall'), (0x10, 'scoopfact')):
        if flags & bit:
            add(group)
    top, convertible, chopped = (bool(flags & bit) for bit in (0x20, 0x80, 0x40))
    if top:
        for group in ('top', 'shield', 'swin'):
            add(group, 0x100)
    if convertible:
        add('convertible', 0x100, 3)
        add('shield', 0x100)
        add('swin', 0x100, 3)
    if chopped:
        for group in ('topchop', 'shieldchop', 'swinchop'):
            add(group, 0x100)
    if flags & 0x20000:
        add('cagechop' if chopped else 'cage', 0x100)
    for bit, group in ((0x800, 'bumper'), (0x100, 'rmirror'), (0x200, 'lmirror')):
        if flags & bit:
            add(group)
    if flags & 0x400:
        add('skirt')
    add('wheelwell')
    add('ffender' if flags & 0x1000 else 'fenderlight')
    for bit, group in ((0x2000, 'rfender'), (0x4000, 'boards'),
                       (0x8000, 'chin'), (0x10000, 'firewall')):
        if flags & bit:
            add(group)
    if not (top or convertible or chopped):
        add('shield', 0x100)
    return tuple(records + selected)
