"""Explicit local data root, case-insensitive lookup on all operating systems."""
from pathlib import Path
from .fce import decode
from tools.viv import read_member
from .textures import decode_fsh


class Assets:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError(f'data root does not exist: {self.root}')
        self.paths = {}
        for path in self.root.rglob('*'):
            if path.is_file():
                relative = path.relative_to(self.root).as_posix().casefold()
                if relative in self.paths:
                    raise ValueError(f'case-ambiguous asset paths: {relative}')
                if not path.resolve().is_relative_to(self.root):
                    raise ValueError(f'asset symlink leaves data root: {relative}')
                self.paths[relative] = path

    def vehicles(self):
        return sorted(path for key, path in self.paths.items()
                      if key.startswith('data/models/') and key.endswith('.viv'))

    def load_vehicle(self, path):
        return decode(read_member(path, 'part.fce'))

    def load_textures(self, path, skin=None):
        if skin:
            key=('data/skins/'+skin).casefold()
            if key not in self.paths:
                raise ValueError(f'skin not found: {skin}')
            return decode_fsh(self.paths[key].read_bytes())
        try:
            data=read_member(path,'part.fsh')
        except KeyError:
            return ()
        return decode_fsh(data)
