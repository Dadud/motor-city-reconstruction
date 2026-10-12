"""Body render-group selection recovered from mcity 0x52d710 / 0x52db70.

This selects visual body groups only, including reconstructed stock flags.
Named profiles are preview choices; attached components are not assembled here.
"""
from .fce import Model

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


def stock_body_flags(model, stock_parts):
    """0x52e880 visual flags, using ordered installed component identities.

    This does not use StockAssembly.ConfigDefault as a visibility switch.
    It expects the catalogue's resolved part filename, before VIV path expansion.
    """
    names = {part.name for part in model.parts}
    available = 0x40000
    for group, bit in AVAILABLE_GROUPS:
        if ':H'+group in names:
            available |= bit
    installed = 0x40000 | (available & 0x300)  # Mirrors present by default.
    blower = next((p for p in stock_parts if p.abstract_type_id == 340333), None)
    scoop = next((p for p in stock_parts if p.abstract_type_id == 350001), None)
    for kind, attachment, options in CONFIGURATION:
        part = next((p for p in stock_parts if p.abstract_type_id == kind and
                     (not attachment or p.attachment_id == attachment)), None)
        if part is None:
            continue
        filename = part.filename or ''
        if kind == 40001:
            if blower is not None and blower.filename:
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
