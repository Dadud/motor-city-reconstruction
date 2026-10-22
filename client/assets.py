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

    def track_file(self, track_name, suffix, night=False, wet=False):
        """Resolve a track resource using the native Tr{variant}{suffix} order.

        REA's static analysis of mcity.exe 0x4287f0 shows that the night and
        wet flags select ``nw``, ``n``, then ``w`` variants (when enabled),
        before the unconditional base ``Tr`` file. The caller supplies the
        resource tail, such as ``.frd`` or ``0.fsh``; this method does not
        decode or load its contents.
        """
        if (not isinstance(track_name, str) or not track_name
                or track_name in {'.', '..'}
                or any(char in track_name for char in '/\\:')):
            raise ValueError(f'invalid track name: {track_name!r}')
        if (not isinstance(suffix, str) or not suffix
                or any(char in suffix for char in '/\\:')):
            raise ValueError(f'invalid track resource suffix: {suffix!r}')

        variants = []
        if night and wet:
            variants.append('nw')
        if night:
            variants.append('n')
        if wet:
            variants.append('w')
        variants.append('')

        directory = f'data/tracks/{track_name}/'.casefold()
        for variant in variants:
            key = f'{directory}tr{variant}{suffix}'.casefold()
            if key in self.paths:
                return self.paths[key]
        # The native resolver returns the ordinary path even when no
        # candidate exists; preserve that behavior for downstream open calls.
        return self.root / 'Data' / 'Tracks' / track_name / f'Tr{suffix}'

    def load_sky_resources(self, track_name, *, night=False, wet=False,
                            cloud_count=0, clouds_enabled=True):
        """Decode the track sky archive using the native lighting-mode table."""
        from .sky import load_sky_resources
        if (not isinstance(track_name, str) or not track_name
                or track_name in {'.', '..'}
                or any(char in track_name for char in '/\\:')):
            raise ValueError(f'invalid track name: {track_name!r}')
        key = f'data/tracks/{track_name}/sky.fsh'.casefold()
        path = self.paths.get(key)
        if path is None:
            return None
        return load_sky_resources(path.read_bytes(), night=night, wet=wet,
                                  cloud_count=cloud_count,
                                  clouds_enabled=clouds_enabled)

    def load_vehicle(self, path):
        return decode(self.load_vehicle_bytes(path))

    def load_vehicle_bytes(self, path):
        """Return the original complete FCE image for verified preparation."""
        return read_member(path, 'part.fce')

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
