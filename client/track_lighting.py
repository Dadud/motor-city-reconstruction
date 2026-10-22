"""Track lighting options consumed by the native scenery color loader."""
from pathlib import Path


def track_lighting_ini(track_directory, *, night=False, weather=False):
    """Return the native Tr*.ini variant selected by the two track flags."""
    suffix = ('N' if night else '') + ('W' if weather else '')
    return Path(track_directory) / f'Tr{suffix}.ini'


def read_object_color_percentages(path):
    """Read the RGB percentages consumed by native FUN_00428500.

    The client reads AmbientRed/Green/Blue from the selected track INI's
    ``[light]`` section, then clamps each setting to the inclusive range 0..200.
    Missing values retain the native initialized neutral value of 100.
    """
    values = {'ambientred': 100, 'ambientgreen': 100, 'ambientblue': 100}
    in_light = False
    try:
        lines = Path(path).read_text(encoding='latin-1').splitlines()
    except OSError as exc:
        raise ValueError(f'cannot read track lighting file: {path}') from exc
    for raw in lines:
        line = raw.split(';', 1)[0].split('#', 1)[0].strip()
        if not line:
            continue
        if line.startswith('[') and line.endswith(']'):
            if in_light:
                break
            in_light = line[1:-1].strip().casefold() == 'light'
            continue
        if in_light and '=' in line:
            key, value = (part.strip() for part in line.split('=', 1))
            key = key.casefold()
            if key in values:
                try:
                    number = int(value, 10)
                except ValueError as exc:
                    raise ValueError(f'invalid {key} value in {path}') from exc
                values[key] = min(200, max(0, number))
    return values['ambientred'], values['ambientgreen'], values['ambientblue']

