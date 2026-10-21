"""Prepared-model union, recentering and chassis extents from 0x52be40.

Attachment/tire and suspension placement must have run first. Graph identity is
represented by model indices so distinct component nodes can retain aliases to
the same FCE image.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import struct
from fractions import Fraction

from client.tire_response import f32


@dataclass(frozen=True)
class SelectedPart:
    model: int
    part: int
    flags: int = 0
    node_type: int = 0


@dataclass(frozen=True)
class PreparedModelGroup:
    models: tuple[bytes, ...]
    model_order: tuple[int, ...]
    selected_parts: tuple[SelectedPart, ...]
    owner_flags: int = 0
    reference_part: SelectedPart | None = None
    secondary_model: int | None = None


@dataclass(frozen=True)
class ModelGroupResult:
    group: PreparedModelGroup
    half_extents: tuple[float, float, float]
    center_translation: tuple[float, float, float]
    selected_bounds: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    secondary_aligned: bool


@dataclass(frozen=True)
class VehicleModelPreparationResult:
    result: ModelGroupResult
    tire_results: tuple[TirePreparationResult, ...]
    suspension_result: SuspensionPreparationResult


def prepare_vehicle_model_group(group: PreparedModelGroup, components,
                                tire_positions=(1, 2, 4, 3)):
    """Compose the observed preparation order inside original 0x52be40.

    The caller supplies the already-loaded owner/model graph and selected-part
    list. This preserves aliased model indices and does not construct nodes,
    load VIV archives, or claim the upstream owner startup is complete.
    """
    components = tuple(components)
    models = tuple(group.models)
    tire_results = []
    for position in tire_positions:
        prepared = prepare_tire_models(models, components, position)
        models = prepared.models
        tire_results.append(prepared)
    suspension = prepare_rear_suspension_model(models, components)
    models = suspension.models
    final_group = replace(group, models=models)
    result = prepare_model_group(final_group)
    return VehicleModelPreparationResult(result, tuple(tire_results), suspension)


def _round_fraction_f32(value):
    """Round an exact rational directly to binary32, avoiding double-rounding."""
    if value == 0:
        return 0.0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if exponent >= 0:
        if magnitude < (1 << exponent):
            exponent -= 1
    elif magnitude < Fraction(1, 1 << -exponent):
        exponent -= 1
    scaled = (magnitude / (1 << exponent) if exponent >= 0
              else magnitude * (1 << -exponent))
    mantissa = round(scaled * (1 << 23))
    if mantissa == (1 << 24):
        mantissa >>= 1
        exponent += 1
    word = sign | ((exponent + 127) << 23) | (mantissa - (1 << 23))
    return struct.unpack('<f', struct.pack('<I', word))[0]


@dataclass(frozen=True)
class TireModelComponent:
    class_id: int
    position: int
    model: int
    width_mm: float = 0.0
    aspect_percent: float = 0.0
    rim_inches: float = 0.0


@dataclass(frozen=True)
class TirePreparationResult:
    models: tuple[bytes, ...]
    prepared: bool
    radius_m: float | None = None
    width_m: float | None = None
    size_scales: tuple[float, float] | None = None


@dataclass(frozen=True)
class SuspensionPreparationResult:
    models: tuple[bytes, ...]
    prepared: bool
    scale_x: float | None = None


def prepare_rear_suspension_model(models, components) -> SuspensionPreparationResult:
    """Translate rear suspension/tire geometry alignment from 0x52b7c0."""
    models = [bytearray(image) for image in models]
    components = tuple(components)
    for image in models:
        _layout(image)
    wheel = next((item for item in components
        if item.class_id == 0x1adb1 and item.position == 3), None)
    if wheel is None:
        wheel = next((item for item in components
            if item.class_id == 0x1adb1 and item.position == 4), None)
    suspension = next((item for item in components if item.class_id == 0x3e9), None)
    if wheel is None or suspension is None or wheel.model is None or suspension.model is None:
        return SuspensionPreparationResult(tuple(bytes(image) for image in models), False)
    if not (0 <= wheel.model < len(models) and 0 <= suspension.model < len(models)):
        raise ValueError('wheel or suspension references an invalid model')
    tire_image, suspension_image = models[wheel.model], models[suspension.model]

    # Original 0x4c5ca0 compares the complete marker name, including ':'
    # and the terminating NUL; this is not a substring search.
    def marker_index(image, expected_name):
        count = struct.unpack_from('<I', image, 0x11c)[0]
        for index in range(count):
            start = 0xe28 + index*0x40
            actual = bytes(image[start:start+0x40]).split(b'\0', 1)[0]
            if actual == expected_name:
                return index
        return -1

    suspension_part = marker_index(suspension_image, b':PHrearsusp')
    tire_part = marker_index(tire_image, b':PHtire')
    if suspension_part < 0 or tire_part < 0:
        return SuspensionPreparationResult(tuple(bytes(image) for image in models), False)
    tire_origin = struct.unpack_from('<3f', tire_image, 0x120+tire_part*12)
    radius = abs(tire_origin[0])
    half_x = struct.unpack_from('<I', suspension_image, 0x520+suspension_part*4)[0]
    from client.model_preparation import part_half_extents, scale_part_streams
    half_extents = part_half_extents(suspension_image, suspension_part)
    if radius == 0 or half_extents is None or half_extents[0] == 0:
        return SuspensionPreparationResult(tuple(bytes(image) for image in models), False)
    diameter = f32(radius + radius)
    denominator = f32(half_extents[0] + half_extents[0])
    from client.startup_record import _round_mant64
    scale = _round_fraction_f32(_round_mant64(
        Fraction.from_float(float(diameter)) /
        Fraction.from_float(float(denominator))))
    scale_part_streams(suspension_image, suspension_part, (scale, 1.0, 1.0))
    target = 0x120 + suspension_part*12
    struct.pack_into('<f', suspension_image, target, 0.0)
    struct.pack_into('<2f', suspension_image, target+4, *tire_origin[1:])
    return SuspensionPreparationResult(tuple(bytes(image) for image in models), True, scale)


def prepare_tire_models(models, components, position) -> TirePreparationResult:
    """Translate original tire geometry placement helper 0x52b950.

    Inputs are the already-loaded component/model graph in original list order.
    The first type-0x1adb1 component at ``position`` supplies tire dimensions;
    the first matching ``:PH`` part with valid nonzero bounds supplies its model
    template. Matching tire/rim/brake models are then translated and scaled.
    """
    models = [bytearray(image) for image in models]
    components = tuple(components)
    if not 0 <= position <= 0xffffffff:
        raise ValueError('tire position must be uint32')
    for image in models:
        _layout(image)
    selected = next((item for item in components
        if item.class_id == 0x1adb1 and item.position == position), None)
    if selected is None or selected.model is None:
        return TirePreparationResult(tuple(bytes(image) for image in models), False)
    if not 0 <= selected.model < len(models):
        raise ValueError('selected tire references an invalid model')
    width_mm, aspect, rim = map(f32,
        (selected.width_mm, selected.aspect_percent, selected.rim_inches))
    # The original forms radius as one x87 expression and stores it once;
    # rounding the intermediate width term to float32 changes boundary cases.
    from client.startup_record import _round_mant64
    exact = lambda value: Fraction.from_float(float(value))
    aspect_term = _round_mant64(exact(aspect) * exact(f32(0.01)))
    width_term = _round_mant64(exact(width_mm) * exact(f32(0.001)))
    width_term = _round_mant64(width_term * aspect_term)
    doubled = _round_mant64(width_term + width_term)
    rim_term = _round_mant64(exact(rim) * exact(f32(0.0254)))
    radius_x87 = _round_mant64(_round_mant64(rim_term + doubled) * exact(0.5))
    radius = _round_fraction_f32(radius_x87)
    width = f32(width_mm * f32(0.001))
    if radius == 0 or width == 0:
        return TirePreparationResult(tuple(bytes(image) for image in models), False)
    adjusted_radius = max(f32(radius - f32(0.3700000047683716)), 0.0)
    adjusted_width = f32(width - f32(0.23000000417232513))
    template = None
    for item in components:
        if item.class_id != 0x1adb1 or item.position != position or item.model is None:
            continue
        if not 0 <= item.model < len(models):
            raise ValueError('tire component references an invalid model')
        image = models[item.model]
        count = struct.unpack_from('<I', image, 0x11c)[0]
        for part in range(count):
            start = 0xe28 + part*0x40
            name = bytes(image[start:start+0x40]).split(b'\0', 1)[0]
            if b':PH' not in name:
                continue
            from client.model_preparation import part_half_extents
            half = part_half_extents(image, part)
            if half is None:
                continue
            lateral = max(half[1], half[2])
            if lateral != 0 and half[0] != 0:
                vertical = _round_mant64(exact(radius) / exact(lateral))
                horizontal = _round_mant64(exact(width) /
                    exact(f32(half[0] + half[0])))
                template = (_round_fraction_f32(vertical),
                            _round_fraction_f32(horizontal))
                break
        if template is not None:
            break
    if template is None:
        return TirePreparationResult(tuple(bytes(image) for image in models), False)
    vertical_scale, lateral_scale = template
    for item in components:
        if item.position != position or item.class_id not in (0x1adb1, 0x186a1, 0x1d4c1) or item.model is None:
            continue
        if not 0 <= item.model < len(models):
            raise ValueError('attached tire model references an invalid image')
        image = models[item.model]
        count = struct.unpack_from('<I', image, 0x11c)[0]
        for part in range(count):
            origin_offset = 0x120 + part*12
            x, y, z = struct.unpack_from('<3f', image, origin_offset)
            y = f32(y - adjusted_radius)
            x = f32(x - adjusted_width) if x >= 0 else f32(adjusted_width + x)
            struct.pack_into('<3f', image, origin_offset, x, y, z)
            from client.model_preparation import scale_part_streams
            scale_part_streams(image, part, (lateral_scale, vertical_scale,
                                              vertical_scale))
    return TirePreparationResult(tuple(bytes(image) for image in models), True,
        radius, width, (lateral_scale, vertical_scale))


def _layout(image):
    if len(image) < 0x2038:
        raise ValueError('complete FCE image required')
    part_count = struct.unpack_from('<I', image, 0x11c)[0]
    dummy_count = struct.unpack_from('<I', image, 0x58)[0]
    if part_count > 64 or dummy_count > 16:
        raise ValueError('bounded FCE part and dummy counts required')
    for index in range(part_count):
        first = struct.unpack_from('<I', image, 0x420 + index*4)[0]
        count = struct.unpack_from('<I', image, 0x520 + index*4)[0]
        start = 0x2038 + struct.unpack_from('<I', image, 0x14)[0] + first*12
        if count > 1_000_000 or start + count*12 > len(image):
            raise ValueError('bounded FCE vertex range required')
    if 0x5c + dummy_count*12 > len(image) or 0x120 + part_count*12 > len(image):
        raise ValueError('bounded FCE origin tables required')
    return part_count, dummy_count


def _part_bounds(image, part, mirrored):
    count, _ = _layout(image)
    if not 0 <= part < count:
        return None
    first = struct.unpack_from('<I', image, 0x420 + part*4)[0]
    vertices = struct.unpack_from('<I', image, 0x520 + part*4)[0]
    if not vertices:
        return None
    stream = 0x2038 + struct.unpack_from('<I', image, 0x14)[0] + first*12
    origin = struct.unpack_from('<3f', image, 0x120 + part*12)
    low = high = None
    for index in range(vertices):
        point = struct.unpack_from('<3f', image, stream + index*12)
        if not all(math.isfinite(value) for value in (*point, *origin)):
            raise ValueError('finite FCE geometry required')
        position = tuple(f32((-x if mirrored else x) + o)
                         for x, o in zip(point, origin))
        if low is None:
            low = high = position
        else:
            low = tuple(candidate if candidate < old else old
                        for old, candidate in zip(low, position))
            high = tuple(candidate if candidate > old else old
                         for old, candidate in zip(high, position))
    return low, high


def prepare_model_group(group: PreparedModelGroup) -> ModelGroupResult:
    """Run the bounds/centering tail of 0x52be40 on already-prepared images.

    The selected-part bound is the union of valid, nonempty selected parts.
    All part and dummy origins in model_order are translated. If a secondary
    model is present, the original selected type-0x11 reference must be given.
    """
    if not isinstance(group, PreparedModelGroup):
        raise TypeError('PreparedModelGroup required')
    models = [bytearray(image) for image in group.models]
    if not models or not group.model_order:
        raise ValueError('at least one prepared model is required')
    if any(type(index) is not int or not 0 <= index < len(models)
           for index in group.model_order):
        raise ValueError('model order contains an invalid model index')
    if type(group.owner_flags) is not int or not 0 <= group.owner_flags <= 0xffffffff:
        raise ValueError('owner flags must be uint32')
    for image in models:
        _layout(image)
    low = high = None
    have_bounds = False
    for selected in group.selected_parts:
        if not isinstance(selected, SelectedPart):
            raise TypeError('SelectedPart records required')
        if not 0 <= selected.model < len(models):
            raise ValueError('selected part references an invalid model')
        bounds = _part_bounds(models[selected.model], selected.part,
                              bool(selected.flags & 0x40))
        if bounds is None:
            continue
        part_low, part_high = bounds
        if low is None:
            low, high = part_low, part_high
            have_bounds = True
        else:
            low = tuple(candidate if candidate < old else old
                        for old, candidate in zip(low, part_low))
            high = tuple(candidate if candidate > old else old
                         for old, candidate in zip(high, part_high))
    if low is None:
        low = high = (0.0, 0.0, 0.0)
        extents = (0.0, 0.0, 0.0)
    else:
        extents = tuple(f32(f32(upper - lower) * 0.5)
                        for lower, upper in zip(low, high))
    translation = tuple(f32((upper + lower) * -0.5)
                        for lower, upper in zip(low, high))
    for index in group.model_order:
        image = models[index]
        parts, dummies = _layout(image)
        for offset, count in ((0x120, parts), (0x5c, dummies)):
            for item in range(count):
                point = struct.unpack_from('<3f', image, offset + item*12)
                struct.pack_into('<3f', image, offset + item*12,
                                 *(f32(value + shift)
                                   for value, shift in zip(point, translation)))
    aligned = False
    if group.secondary_model is not None:
        if group.reference_part is None:
            raise ValueError('secondary alignment requires the selected reference part')
        if not 0 <= group.secondary_model < len(models):
            raise ValueError('secondary model index is invalid')
        reference = group.reference_part
        if reference.node_type != 0x11:
            raise ValueError('secondary alignment reference must have node type 0x11')
        from client.model_preparation import align_secondary_model
        aligned = align_secondary_model(models[group.secondary_model],
            models[reference.model], reference.part)
    if not group.owner_flags & 0x40:
        for selected in group.selected_parts:
            if selected.node_type not in (0x10, 0x11, 0x12):
                continue
            image = models[selected.model]
            parts, _ = _layout(image)
            if 0 <= selected.part < parts:
                offset = 0x120 + selected.part*12 + 4
                value = struct.unpack_from('<f', image, offset)[0]
                struct.pack_into('<f', image, offset, f32(value + 0.05))
    result = PreparedModelGroup(tuple(bytes(image) for image in models),
        group.model_order, group.selected_parts, group.owner_flags,
        group.reference_part, group.secondary_model)
    return ModelGroupResult(result, extents, translation,
                            (low, high) if have_bounds else None, aligned)
