"""Translate the 0x494070 and 0x4940f0 track sky initialization path."""
from dataclasses import dataclass
import struct

from .textures import Texture, decode_fsh


# Eight pointers per mode, read from the tables selected by 0x494070.
# Their final entries intentionally overlap neighboring runs in the shared
# pointer pool; preserve the eight native positions exactly.
_RESOURCE_TABLES = {
    (False, False): ('CLDD', 'CLD2', 'CHRD', 'SUND', 'VAMD', 'VMD2', 'HDC%d', None),
    (False, True):  ('CLWD', 'CL2W', 'CHRW', 'SUNW', 'VADW', 'VDW2', 'HDW%d', 'CLDD'),
    (True, False):  ('CLDN', 'CL2N', 'CHRN', 'SUNN', 'VAMN', 'VMN2', 'HNC%d', 'CLWD'),
    (True, True):   ('CLWN', 'C2WN', 'CHNW', 'SNNW', 'VMNW', 'VNW2', 'HNW%d', 'CLDN'),
}
_GRID_SIZE = 26
_NATIVE_STEP = struct.unpack('<f', struct.pack('<f', 0.03846154))[0]


@dataclass(frozen=True)
class SkyLookup:
    """A native 26×26 RGBA lookup texture and its table position."""
    name: str
    table_index: int
    rgba: bytes


@dataclass(frozen=True)
class SkyResources:
    """Decoded resources selected from one track's sky.fsh archive."""
    names: tuple[str | None, ...]
    primary: tuple[Texture | None, ...]
    lookups: tuple[SkyLookup | None, ...]
    cloud_pattern: str
    clouds: tuple[str, ...]


def sky_resource_names(*, night=False, wet=False):
    """Return the exact eight names/pattern slots selected by native flags."""
    if type(night) is not bool or type(wet) is not bool:
        raise ValueError('night and wet must be booleans')
    return _RESOURCE_TABLES[(night, wet)]


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _sample_26(texture):
    """Sample the native rounded and edge-clamped 26x26 color grid."""
    width, height = texture.width, texture.height
    pixels = texture.rgba
    if width <= 0 or height <= 0 or len(pixels) != width * height * 4:
        raise ValueError(f'invalid decoded texture buffer: {texture.name}')
    step_x = _f32(width * _NATIVE_STEP)
    step_y = _f32(height * _NATIVE_STEP)
    output = bytearray(_GRID_SIZE * _GRID_SIZE * 4)
    for y in range(_GRID_SIZE):
        source_y = min(height - 1, max(0, int(round(_f32(y * step_y)))))
        for x in range(_GRID_SIZE):
            source_x = min(width - 1, max(0, int(round(_f32(x * step_x)))))
            source = (source_y * width + source_x) * 4
            target = (y * _GRID_SIZE + x) * 4
            output[target:target + 4] = pixels[source:source + 4]
    return bytes(output)


def load_sky_resources(data, *, night=False, wet=False, cloud_count=0,
                       clouds_enabled=True):
    """Decode the native selected archive resources and 26x26 lookup grids.

    ``cloud_count`` corresponds to the caller-owned native count global. Cloud
    names follow the table's `%d` pattern and stop at the first missing image,
    matching the native flag clear that suppresses later dynamic lookups.
    Direct3D upload and rendering are outside this asset decoder.
    """
    names = sky_resource_names(night=night, wet=wet)
    if type(cloud_count) is not int or not 0 <= cloud_count <= 256:
        raise ValueError('cloud_count must be an integer in 0..256')
    if type(clouds_enabled) is not bool:
        raise ValueError('clouds_enabled must be a boolean')

    by_name = {}
    for texture in decode_fsh(data):
        by_name.setdefault(texture.name, texture)
    selected = tuple(by_name.get(name) if name else None for name in names)
    lookups = tuple(
        SkyLookup(texture.name, index, _sample_26(texture)) if texture else None
        for index, texture in enumerate(selected[4:], 4)
    )

    cloud_pattern = names[6]
    clouds = []
    if clouds_enabled:
        for index in range(cloud_count):
            name = cloud_pattern % index
            if name not in by_name:
                break
            clouds.append(name)
    return SkyResources(names, selected[:4], lookups, cloud_pattern, tuple(clouds))


def load_sky_textures(data, *, night=False, wet=False, cloud_count=0,
                      clouds_enabled=True):
    """Return only the native 26x26 lookup entries for existing textures."""
    result = load_sky_resources(data, night=night, wet=wet,
                                cloud_count=cloud_count,
                                clouds_enabled=clouds_enabled)
    return tuple(entry for entry in result.lookups if entry is not None)
