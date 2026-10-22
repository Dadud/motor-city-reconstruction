"""Translate the 0x494070 and 0x4940f0 track sky initialization path."""
from dataclasses import dataclass
import math
import struct

from .random_state import RandomState
from .matrix_math import vector_length3
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


def sky_material_triangle_indices():
    """Return the native 25x25 grid's interleaved row-index pairs."""
    indices = []
    for row in range(1, 26):
        for column in range(25):
            indices.extend((row * 26 - 26 + column, row * 26 + column))
    return tuple(indices)


def sky_material_random_grid(random_state, *, upper_bound, modulus):
    """Produce the transposed 26×26 random height field from 0x4943f0."""
    if not isinstance(random_state, RandomState):
        raise TypeError('random_state must be a RandomState')
    if (type(upper_bound) is not int or type(modulus) is not int or
            not 0 <= upper_bound <= 0x7fffffff or not 0 <= modulus <= 0xffffffff):
        raise ValueError('height bound and random modulus must fit native integer fields')
    values = [0.0] * (26 * 26)
    for row in range(26):
        for column in range(26):
            value = (upper_bound if modulus == 0 else
                     upper_bound - random_state.next_u32() % modulus)
            values[column * 26 + row] = _f32(value)
    return tuple(values)


def sky_material_normalize_grid(values):
    """Apply the native signed-square-root contrast transform to 676 values."""
    if len(values) != 26 * 26:
        raise ValueError('sky material height grid must contain 676 values')
    result = []
    for value in values:
        delta = _f32(_f32(value) - 128.0)
        normalized = _f32(delta * _f32(1.0 / 128.0))
        sign = -1.0 if normalized < 0.0 else 1.0
        signed_root = sign * math.sqrt(abs(normalized))
        result.append(_f32((signed_root + 1.0) * 0.5 * 255.0))
    return tuple(result)


def sky_material_smooth_grid(values, *, upper_bound, passes=20):
    """Apply the native in-place weighted 5x5 height smoothing passes."""
    if len(values) != 26 * 26:
        raise ValueError('sky material height grid must contain 676 values')
    if type(upper_bound) is not int or not 0 <= upper_bound <= 0x7fffffff:
        raise ValueError('height bound must fit the native signed integer field')
    if type(passes) is not int or not 0 <= passes <= 20:
        raise ValueError('smoothing pass count must be within [0, 20]')
    grid = [_f32(value) for value in values]
    for _ in range(passes):
        for row in range(26):
            for column in range(26):
                center_index = column * 26 + row
                center = grid[center_index]
                accumulator = 0.0
                count = 0
                for drow in range(-2, 3):
                    for dcolumn in range(-2, 3):
                        if (drow == 0 and dcolumn == 0 or
                                not 0 <= row + drow < 26 or
                                not 0 <= column + dcolumn < 26):
                            continue
                        neighbor = grid[(column + dcolumn) * 26 + row + drow]
                        scaled_distance = (abs(neighbor) - 128.0) / 128.0
                        weight = 1.0 if abs(drow) <= 1 and abs(dcolumn) <= 1 else 0.5
                        accumulator = _f32(
                            accumulator + scaled_distance * scaled_distance *
                            (neighbor - center) * weight)
                        count += 1
                average = accumulator / count
                if average != 0.0:
                    grid[center_index] = _f32(min(float(upper_bound),
                                                  max(0.0, center + average * 0.5)))
    return tuple(grid)


def sky_material_mesh_outputs(heights, *, angle, row_scale, column_scale,
                             base_offset, amplitude, color_scale, invert=False,
                             texture_rgba=None):
    """Build the two transposed vertex arrays emitted by 0x4943f0.

    The first array contains rotated world positions. The second contains
    unrotated grid coordinates and the packed grayscale height color.
    """
    if len(heights) != 26 * 26:
        raise ValueError('sky material height grid must contain 676 values')
    if texture_rgba is not None and (not isinstance(texture_rgba, bytes) or
                                     len(texture_rgba) != 26 * 26 * 4):
        raise ValueError('texture override must contain 676 RGBA pixels')
    angle = _f32(angle)
    row_scale, column_scale = _f32(row_scale), _f32(column_scale)
    base_offset, amplitude, color_scale = map(_f32, (base_offset, amplitude, color_scale))
    sine, cosine = math.sin(angle * (2.0 * math.pi)), math.cos(angle * (2.0 * math.pi))
    positions, mesh = [None] * 676, [None] * 676
    for row in range(26):
        world_y = -3000.0 + row * 225.0
        for column in range(26):
            world_x = -3000.0 + column * 225.0
            x = _f32(sine * world_y + cosine * world_x)
            z = _f32(cosine * world_y - sine * world_x)
            radius = vector_length3((x, 0.0, z))
            radial_angle = _f32(radius * 0.25 * 0.00033333333)
            profile = _f32(math.cos(radial_angle * (2.0 * math.pi)) * amplitude + base_offset)
            index = column * 26 + row
            pixel = (None if texture_rgba is None else
                     texture_rgba[index*4:(index+1)*4])
            height = (_f32(heights[index]) if pixel is None else
                      float(sum(pixel) // 4))
            fraction = _f32(height * _f32(0.003921569))
            if invert:
                fraction = -fraction
            profile = _f32(profile - amplitude * color_scale * fraction * 0.5)
            shade = int(round(height)) & 0xff
            packed = (shade * 0x01010101 if pixel is None else
                      int.from_bytes(pixel, 'little'))
            positions[index] = (_f32(x), profile, z)
            mesh[index] = (_f32(column * column_scale * 0.5),
                           _f32(row * row_scale * 0.5), packed)
    return tuple(positions), tuple(mesh)


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

    def material_lookup_rgba(self, block_index):
        """Return the sampled table-4/5 RGBA buffer for material block 0/1.

        The native loader walks `param_2[4]` and `[5]` into the two
        `0x4943f0` blocks at `0x9b88d4` and `0x9c4a0c`, respectively.
        """
        if type(block_index) is not int or block_index not in (0, 1):
            raise ValueError('sky material block index must be 0 or 1')
        lookup = self.lookups[block_index]
        return None if lookup is None else lookup.rgba


def sky_resource_names(*, night=False, wet=False):
    """Return the exact eight names/pattern slots selected by native flags."""
    if type(night) is not bool or type(wet) is not bool:
        raise ValueError('night and wet must be booleans')
    return _RESOURCE_TABLES[(night, wet)]


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _i32(value):
    return value if value < 0x80000000 else value - 0x100000000


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


@dataclass(frozen=True)
class SkyMaterialOutput:
    """Recovered data products of one procedural sky-material block."""
    triangle_indices: tuple[int, ...]
    random_heights: tuple[float, ...]
    normalized_heights: tuple[float, ...]
    smoothed_heights: tuple[float, ...]
    positions: tuple[tuple[float, float, float], ...]
    mesh: tuple[tuple[float, float, int], ...]


@dataclass(frozen=True)
class PreparedSkyMaterialParameters:
    """Normalized parameter fields prepared by the native 0x494dc0 helper."""
    height_bound: int
    random_modulus: int
    random_reciprocal: float
    column_scale: float
    row_scale: float
    angle_cycles: float
    radial_scale: float
    profile_cosine: float
    profile_sine: float


def prepare_sky_material_parameters(*, height_bound, random_modulus,
                                    random_divisor, random_reciprocal,
                                    column_scale, row_scale,
                                    angle_degrees, radial_distance):
    """Translate 0x494dc0's bounds, scale defaults, and radial terms."""
    int_fields = (height_bound, random_modulus, random_divisor,
                  angle_degrees, radial_distance)
    if any(type(value) is not int or not -0x80000000 <= value <= 0x7fffffff
           for value in int_fields):
        raise ValueError('sky parameter integer fields must be signed 32-bit values')
    height_bound = _i32(height_bound)
    random_modulus = _i32(random_modulus)
    random_divisor = _i32(random_divisor)
    if height_bound < 0 or random_modulus < 0:
        raise ValueError('height bound and random modulus must be non-negative')
    reciprocal = _f32(random_reciprocal)
    if random_divisor:
        reciprocal = _f32(1.0 / float(random_divisor))
    if height_bound < random_modulus:
        random_modulus = height_bound
    column_scale = _f32(column_scale)
    row_scale = _f32(row_scale)
    if column_scale == 0.0:
        column_scale = 1.0
    if row_scale == 0.0:
        row_scale = 1.0
    angle_cycles = _f32(angle_degrees * _f32(0.0027777778))
    radial_scale = _f32(radial_distance * _f32(3.0e-5))
    cosine = _f32(math.cos(angle_cycles * (2.0 * math.pi)) * radial_scale)
    sine = _f32(math.sin(angle_cycles * (2.0 * math.pi)) * radial_scale)
    return PreparedSkyMaterialParameters(
        height_bound, random_modulus, reciprocal, column_scale, row_scale,
        angle_cycles, radial_scale, cosine, sine)


def build_sky_material(random_state, *, upper_bound, modulus, angle, row_scale,
                       column_scale, base_offset, amplitude, color_scale,
                       invert=False, texture_rgba=None):
    """Run the recovered procedural sky-material stages as one pipeline."""
    random_heights = sky_material_random_grid(
        random_state, upper_bound=upper_bound, modulus=modulus)
    normalized = sky_material_normalize_grid(random_heights)
    smoothed = sky_material_smooth_grid(normalized, upper_bound=upper_bound)
    positions, mesh = sky_material_mesh_outputs(
        smoothed, angle=angle, row_scale=row_scale, column_scale=column_scale,
        base_offset=base_offset, amplitude=amplitude, color_scale=color_scale,
        invert=invert, texture_rgba=texture_rgba)
    return SkyMaterialOutput(sky_material_triangle_indices(), random_heights,
                            normalized, smoothed, positions, mesh)
