"""Per-user settings; never write into the installed game's directory."""
import json
import os
from pathlib import Path
import sys


def settings_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return root / 'MotorCityReconstruction' / 'settings.json'


def load():
    try:
        value = json.loads(settings_path().read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save(values):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values, indent=2), encoding='utf-8')
    temporary.replace(path)
