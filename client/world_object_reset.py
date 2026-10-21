"""Evidence-bounded owner reset logic from original routine 0x43b750."""
from dataclasses import dataclass
import struct

from .tire_response import f32
from .track_topology import (bounded_path_index, reset_path_index,
                             reset_track_attribute)
from .travel_map import TravelMapCache, mark_travel_map
from .mouse_controller import cursor_reset_action
from .world_object_path_reset import PathResetGlobals, update_path_reset_state


OWNER_SIZE = 0x1C98
INITIALIZED_BYTES = 0x3C


def reset_world_object_prefix(record, shared_reset_value):
    """Port 0x43b750 through its first child call at 0x53d640.

    This covers the scalar/vector reset and flag preparation immediately
    before later reset subsystems run. The shared value is the observed
    ``DAT_0098c468`` dword copied into both owner fields.
    """
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if type(shared_reset_value) is not int or not 0 <= shared_reset_value <= 0xFFFFFFFF:
        raise ValueError('shared reset value must be uint32')

    for offset in (0x38, 0x3c, 0x40,
                   0xa54, 0xa58, 0xa5c,
                   0xa48, 0xa4c, 0xa50,
                   0xa30, 0xa34, 0xa38,
                   0xa9c):
        struct.pack_into('<I', record, offset, 0)
    for offset in (0xbe8, 0xbec, 0xbf0):
        struct.pack_into('<I', record, offset, 0x47c35000)  # 100000.0f

    record[0x3c4:0x3c4 + INITIALIZED_BYTES] = bytes(INITIALIZED_BYTES)
    for offset in (0x3cc, 0x3d0, 0x3d4):
        struct.pack_into('<I', record, offset, 0)
    struct.pack_into('<II', record, 0x410,
                     shared_reset_value, shared_reset_value)
    struct.pack_into('<H', record, 0x3bc, 1)
    struct.pack_into('<II', record, 0x3c4, 0, 0)

    flags = struct.unpack_from('<I', record, 0xdf4)[0]
    struct.pack_into('<I', record, 0xdf4, flags & 0xfffffeff)
    for offset in (0x122c, 0x1230, 0x1198, 0x119c, 0x11bc):
        struct.pack_into('<I', record, offset, 0)
    flags = struct.unpack_from('<I', record, 0xe14)[0]
    struct.pack_into('<I', record, 0xe14, flags & 0xffffff3f)
    if record[0x474] & 0x10 == 0:
        record[0xe50] = 1
    return record


def reset_world_object_geometry(record, *, reset_component, update_attachment):
    """Port 0x53d640's owner writes around its two reset child routines."""
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if not callable(reset_component) or not callable(update_attachment):
        raise ValueError('both 0x53d4a0 and 0x549660 children are required')

    for offset in (0xa62, 0xa68, 0xa69):
        record[offset] = 1
    for offset in (0x24, 0x30):
        struct.pack_into('<I', record, offset, 0xc11cf5c3)
    record[0xc10:0xc10 + 36] = record[0x78:0x78 + 36]

    for offset in (0xa66, 0xa60, 0xa67, 0xa61, 0xa6a, 0xa88, 0xa6b):
        record[offset] = 0
    for offset in (0xa94, 0xa90, 0xa8c, 0xa74, 0x20, 0x28,
                   0x44, 0x48, 0x4c, 0x2c, 0x34,
                   0xa30, 0xa34, 0xa38, 0xa48, 0xa4c, 0xa50,
                   0xa2c, 0xa3c, 0xa40, 0xa44, 0xa54, 0xa58, 0xa5c,
                   0x14, 0x18, 0x1c, 0x38, 0x3c, 0x40,
                   0xc04, 0xc00, 0xbf4, 0xbf8, 0xbfc, 0xc08):
        struct.pack_into('<I', record, offset, 0)
    struct.pack_into('<H', record, 0xa6e, 0)
    record[0xa89] = 2
    struct.pack_into('<I', record, 0xc0c, 0x3f800000)
    record[0xc34:0xc34 + 36] = record[0x9c:0x9c + 36]

    reset_component(record)
    flags = struct.unpack_from('<I', record, 0x478)[0]
    struct.pack_into('<I', record, 0x478, flags & 0xfffff7ff)
    update_attachment(record)
    return record


def prepare_world_object_reset(record, shared_reset_value, *,
                               reset_component, update_attachment):
    """Compose 0x43b750's prefix with translated child 0x53d640.

    The outer routine continues with additional behavior after this boundary;
    this helper intentionally ends before its next child, 0x43f090.
    """
    reset_world_object_prefix(record, shared_reset_value)
    return reset_world_object_geometry(record,
        reset_component=reset_component, update_attachment=update_attachment)


@dataclass
class WheelResetCache:
    """Process-global lazy cache used by 0x53d4a0."""
    initialized: bool
    factor: float


def reset_wheel_records(record, *, cache, profile_scale):
    """Port 0x53d4a0's four wheel-record initialization loop.

    ``profile_scale`` is the value addressed through owner +0x1c94, +0x20.
    Its quarter is cached once process-wide, matching the original global
    initialization flag and factor.
    """
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if not isinstance(cache, WheelResetCache) or type(cache.initialized) is not bool:
        raise ValueError('the original process-global wheel reset cache is required')
    scale = f32(profile_scale)
    if not cache.initialized:
        cache.factor = f32(scale * 0.25)
        cache.initialized = True
    else:
        cache.factor = f32(cache.factor)

    struct.pack_into('<I', record, 0x478,
                     struct.unpack_from('<I', record, 0x478)[0] & 0xfffff7ff)
    record[0x1224:0x1226] = b'\0\0'
    for index in range(4):
        base = 0x600 + index * 0x10c
        record[0x11ec + index] = 0
        struct.pack_into('<I', record, 0x11dc + index * 4, 0)
        record[0x1220 + index] = 0
        record[base + 0x10:base + 0x10 + 0x44] = record[0x370:0x370 + 0x44]
        struct.pack_into('<I', record, base + 0x54,
                         struct.unpack_from('<I', record, 0x404)[0])
        for offset in range(0x60, 0x90, 4):
            struct.pack_into('<I', record, base + offset, 0)
        struct.pack_into('<f', record, base + 0xd0, f32(cache.factor))
        for offset in (-4, 0, 4, 8, 12):
            struct.pack_into('<I', record, base + offset, 0)
        struct.pack_into('<II', record, base + 0x58, 0x3f800000, 0x3f4ccccd)
        for offset in (0xac, 0xb0, 0xcc, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4):
            struct.pack_into('<I', record, base + offset, 0)
        record[base + 0xe8] = 1
        struct.pack_into('<II', record, base + 0xec, 0, 0)
        source_offset = 0x18ec if index < 2 else 0x18f0
        struct.pack_into('<I', record, base + 0xb8,
                         struct.unpack_from('<I', record, source_offset)[0])
    return record


def reset_world_object_drive_prefix(record, profile, *, reset_drive_state):
    """Port 0x549660 through its final virtual dispatch boundary.

    The profile image resolves fields reached through owner +0x1c94. The
    virtual interface and everything after it are deliberately outside this
    prefix; 0x43b570 remains an explicit stateful child callback.
    """
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if not isinstance(profile, (bytes, bytearray, memoryview)) or len(profile) < 0x690:
        raise ValueError('profile image must include fields through +0x68c')
    if not callable(reset_drive_state):
        raise ValueError('the 0x43b570 state-reset child is required')

    profile_mode = struct.unpack_from('<I', profile, 0x68c)[0]
    if profile_mode == 0:
        record[0xa89] = 2
        result = reset_drive_state(record)
        if result:
            record[0xa89] = 2
    else:
        record[0xa89] = 3

    struct.pack_into('<I', record, 0xb54, 1)
    record[0xa69] = record[0xb54]
    record[0xa62] = 2
    struct.pack_into('<H', record, 0xa6e, 100)
    for offset in (0xb2c, 0xb30, 0xb34, 0xb38, 0xb3c, 0xb40, 0xb44, 0xb48, 0xb50):
        struct.pack_into('<I', record, offset, 0)

    active_wheels = tuple(record[0x6c1 + index * 0x10c] != 0 for index in range(4))

    def normalize_rate(value):
        if abs(value) >= 10000.0:
            return value
        for index, active in enumerate(active_wheels):
            if not active:
                continue
            denominator_offset = 0x18ec if index < 2 else 0x18f0
            denominator = struct.unpack_from('<f', record, denominator_offset)[0]
            if denominator == 0.0:
                raise ValueError('active wheel has zero rate denominator')
            numerator = value * struct.unpack_from('<f', profile, 0x374)[0]
            return f32(numerator / denominator)
        return 0.0

    source = struct.unpack_from('<f', record, 0x1898)[0]
    struct.pack_into('<f', record, 0xb5c, normalize_rate(source))
    source = struct.unpack_from('<f', record, 0x1894)[0]
    struct.pack_into('<f', record, 0xb60, normalize_rate(source))

    for offset in (0xb64, 0xaa0, 0xaa4, 0xaac, 0xaa8):
        struct.pack_into('<I', record, offset, 0)
    active_mode = struct.unpack_from('<I', record, 0xae4)[0] & 1
    if active_mode == 0:
        struct.pack_into('<I', record, 0xab4, 0)
        struct.pack_into('<I', record, 0xac4, 0)
    else:
        profile_rate = struct.unpack_from('<I', profile, 0x6c)[0]
        struct.pack_into('<I', record, 0xab4, profile_rate)
        struct.pack_into('<I', record, 0xac4, profile_rate)
        record[0xa88] = 0
    struct.pack_into('<II', record, 0xab8, 0, 0)
    struct.pack_into('<I', record, 0xac8, 0x3f000000)
    struct.pack_into('<I', record, 0xae0, 0)

    steering = struct.unpack_from('<i', record, 0xab4)[0]
    struct.pack_into('<f', record, 0xab0,
                     f32(steering * f32(0.10471976)))
    divisor = struct.unpack_from('<i', record, 0xac0)[0]
    if divisor == 0:
        raise ValueError('reset profile produces a zero steering divisor')
    struct.pack_into('<f', record, 0xabc, f32(steering / divisor))

    value = f32(struct.unpack_from('<f', record, 0xad4)[0] * 0.98)
    struct.pack_into('<f', record, 0xad4, min(1.0, max(0.3, value)))
    for offset in (0xadc, 0xacc):
        value = f32(struct.unpack_from('<f', record, offset)[0] * 0.98)
        struct.pack_into('<f', record, offset, max(20.0, value))
    for offset in range(0xae8, 0xb00, 4):
        struct.pack_into('<I', record, offset, 0)
    flags = struct.unpack_from('<I', record, 0xae4)[0]
    struct.pack_into('<I', record, 0xae4, flags & 0xffffffd3)
    return record


def reset_world_object_drive_state(record, profile, *, reset_drive_state,
                                   interface_result=0):
    """Complete 0x549660 for the zero-result virtual-interface branch."""
    if len(record) < 0xaf0:
        raise ValueError('owner record does not include the drive reset fields')
    virtual_gate = struct.unpack_from('<I', record, 0xae4)[0] & 1
    reset_world_object_drive_prefix(record, profile,
                                    reset_drive_state=reset_drive_state)
    if virtual_gate == 0:
        if type(interface_result) is not int:
            raise ValueError('virtual interface result must be an observed integer')
        if interface_result != 0:
            raise ValueError('nonzero interface results continue into untranslated drive setup')
        flags = struct.unpack_from('<I', record, 0xae4)[0]
        struct.pack_into('<I', record, 0xae4, flags | 1)
    return record


def reset_world_object_track_rate(record, rate, profile):
    """Port the owner writes in 0x53d7b0 after its 0x53d640 child call.

    The child geometry/drive reset is composed by the outer reset pipeline.
    This function covers the rate, derived position, mode, and per-wheel rate
    writes. ``profile`` is the bounded image reached through owner +0x1c94.
    """
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')
    if not isinstance(profile, (bytes, bytearray, memoryview)) or len(profile) < 0x74:
        raise ValueError('profile image must include its integer limit at +0x70')
    rate = f32(rate)
    struct.pack_into('<f', record, 0xa44, rate)
    forward = struct.unpack_from('<f', record, 0xa3c)[0]
    lateral = struct.unpack_from('<f', record, 0xa40)[0]
    for axis, (first, second, third) in enumerate(((0x78, 0x84, 0x90),
                                                   (0x7c, 0x88, 0x94),
                                                   (0x80, 0x8c, 0x98))):
        value = (rate * struct.unpack_from('<f', record, third)[0] +
                 lateral * struct.unpack_from('<f', record, second)[0] +
                 forward * struct.unpack_from('<f', record, first)[0])
        struct.pack_into('<f', record, 0x14 + axis * 4, f32(value))
    struct.pack_into('<I', record, 0xa2c,
                     struct.unpack_from('<I', record, 0xa44)[0])

    scale = struct.unpack_from('<f', record, 0x1818)[0]
    profile_limit = struct.unpack_from('<i', profile, 0x70)[0]
    mode = 2 if rate * scale <= float(profile_limit) else 3
    record[0xa69] = mode
    record[0xa62] = mode
    flags = struct.unpack_from('<I', record, 0xae4)[0]
    struct.pack_into('<I', record, 0xae4, flags | 1)
    struct.pack_into('<I', record, 0xb54, mode)
    # The comparison leaves rate*scale in ST0 for MSVC __ftol; that helper
    # truncates toward zero under the supported default floating-point mode.
    conversion_scale = struct.unpack_from('<f', record,
                                          0x1810 + mode * 4)[0]
    struct.pack_into('<i', record, 0xab4,
                     int(rate * conversion_scale))

    for wheel in range(4):
        base = 0x668 + wheel * 0x10c
        struct.pack_into('<I', record, base - 0x5c,
                         struct.unpack_from('<I', record, 0xa44)[0])
        struct.pack_into('<I', record, base,
                         struct.unpack_from('<I', record, 0xa44)[0])
        denominator = struct.unpack_from('<f', record, base + 0x50)[0]
        if denominator == 0.0:
            raise ValueError(f'wheel {wheel} has a zero track-rate denominator')
        ratio = f32(rate / denominator)
        struct.pack_into('<f', record, base + 0x10, ratio)
    return record


def reset_world_object_track_rate_pipeline(record, rate, profile, *,
                                           reset_component, reset_drive_state):
    """Compose 0x53d7b0 with its 0x53d640 geometry/drive child."""
    reset_world_object_geometry(
        record, reset_component=reset_component,
        update_attachment=lambda owner: reset_world_object_drive_state(
            owner, profile, reset_drive_state=reset_drive_state,
            interface_result=0))
    return reset_world_object_track_rate(record, rate, profile)


def drive_reset_state_result(record, *, owner_address, selected_owner,
                             result_mask):
    """Port the pure selector return from 0x43b570."""
    if not isinstance(record, (bytes, bytearray, memoryview)) or len(record) < 0x478:
        raise ValueError('owner image must contain its reset-selection flags')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff
           for value in (owner_address, selected_owner, result_mask)):
        raise ValueError('owner identities and result mask must be uint32')
    flags = struct.unpack_from('<I', record, 0x474)[0]
    if flags & 0x212:
        return 1
    return result_mask if owner_address == selected_owner else 0


@dataclass(frozen=True)
class WorldObjectResetServices:
    """Observed process state and services for the verified reset prefix."""
    shared_reset_value: int
    profile: bytes
    path_globals: PathResetGlobals
    shared_reset_generation: int
    shared_reset_metadata: int
    primary_path_count: int
    fallback_path_count: int
    path_origin: int
    secondary_path_origin: int
    wrapped_path_mode: int
    reverse_path_mode: int
    reset_motion_value: int
    track_rows: object
    default_track_attribute: int
    track_rate_count: int
    designated_mode: int
    virtual_reset_gate: object
    reset_drive_state: object
    reset_component: object
    path_interface_query: object
    advance_path_state: object
    travel_map_cache: TravelMapCache
    allocate_travel_map: object
    designated_mode_action: object
    mouse_controller_enabled: int
    mouse_controller_initialized: int
    mouse_input_mode: int
    mouse_environment_mode: int
    mouse_position_x: int
    mouse_position_y: int
    set_mouse_state: object
    complete_interface_reset: object

    def __post_init__(self):
        if not isinstance(self.path_globals, PathResetGlobals):
            raise ValueError('path reset globals are required')
        if not isinstance(self.profile, (bytes, bytearray, memoryview)):
            raise ValueError('the original profile image is required')
        callbacks = (self.virtual_reset_gate, self.reset_drive_state,
                     self.reset_component,
                     self.path_interface_query, self.allocate_travel_map,
                     self.advance_path_state,
                     self.designated_mode_action, self.set_mouse_state,
                     self.complete_interface_reset)
        if not all(callable(callback) for callback in callbacks):
            raise ValueError('all stateful original reset services must be supplied')
        if not isinstance(self.travel_map_cache, TravelMapCache):
            raise ValueError('the process travel-map cache is required')


def reset_world_object_path_stage(record, *, services):
    """Compose 0x43b750 through its mapped path-index update.

    The deterministic owner logic is implemented here. Original virtual and
    stateful service calls stay explicit callbacks so callers can bind native
    services or bounded translated implementations without hidden guesses.
    """
    if not isinstance(services, WorldObjectResetServices):
        raise ValueError('WorldObjectResetServices are required')
    if not isinstance(record, bytearray) or len(record) < OWNER_SIZE:
        raise ValueError('a mutable owner image through +0x1c97 is required')

    reset_world_object_prefix(record, services.shared_reset_value)
    reset_world_object_geometry(record,
        reset_component=lambda owner: services.reset_component(owner),
        update_attachment=lambda owner: reset_world_object_drive_state(
            owner, services.profile,
            reset_drive_state=services.reset_drive_state,
            interface_result=0))

    update_path_reset_state(record, globals_=services.path_globals,
        interface_query=services.path_interface_query,
        notify_track_change=lambda row, step: mark_travel_map(
            services.travel_map_cache, row, step,
            path_count=services.path_globals.path_count,
            step_threshold=services.path_globals.step_threshold,
            allocate=services.allocate_travel_map),
        advance_state=services.advance_path_state)

    flags = struct.unpack_from('<I', record, 0xdf4)[0]
    if flags & 0x1000:
        selected_count = (services.primary_path_count
                          if services.primary_path_count != 0
                          else services.fallback_path_count)
        mapped_index = selected_count * services.path_globals.step_threshold
    else:
        current = struct.unpack_from('<i', record, 0x480)[0]
        counter = struct.unpack_from('<i', record, 0x47c)[0]
        offset = counter if current == 0 or counter != 0 else -current
        mapped_index = reset_path_index(
            struct.unpack_from('<i', record, 0x370)[0], offset,
            primary_count=services.primary_path_count,
            fallback_count=services.fallback_path_count,
            primary_origin=services.path_origin,
            secondary_origin=services.secondary_path_origin,
            wrapped_mode=services.wrapped_path_mode,
            reverse_mode=services.reverse_path_mode)
    struct.pack_into('<i', record, 0x368, mapped_index)
    struct.pack_into('<II', record, 0x410,
                     services.shared_reset_generation,
                     services.shared_reset_generation)
    struct.pack_into('<I', record, 0xa9c, services.shared_reset_metadata)

    if services.virtual_reset_gate(0x0f, record) == 0:
        profile_value = struct.unpack_from('<I', services.profile, 0x6c)[0]
        record[0xa69] = 2
        record[0xa62] = 2
        struct.pack_into('<I', record, 0xb54, 2)
        struct.pack_into('<I', record, 0xab4, profile_value)
    else:
        struct.pack_into('<II', record, 0x410,
                         services.reset_motion_value,
                         services.reset_motion_value)
        track_index = bounded_path_index(
            struct.unpack_from('<i', record, 0x370)[0], 1,
            services.fallback_path_count, clamp=bool(services.wrapped_path_mode))
        track_value = reset_track_attribute(
            services.track_rows, track_index, services.reverse_path_mode,
            default_value=services.default_track_attribute)
        # The caller casts fVar5 back to single precision before applying the
        # depth blend, even though its clamp was held in x87 precision.
        selected = f32(min(17.8812, abs(float(track_value) * 0.25)))
        depth = struct.unpack_from('<i', record, 0x5ac)[0]
        if services.track_rate_count < 2 or depth < 1:
            reset_world_object_track_rate_pipeline(
                record, f32(selected), services.profile,
                reset_component=services.reset_component,
                reset_drive_state=services.reset_drive_state)
        else:
            ratio = f32((depth - 1) / (services.track_rate_count - 1))
            ratio = min(1.0, max(0.0, ratio))
            scaled = f32(((ratio * 0.25) + 0.75) * selected)
            reset_world_object_track_rate_pipeline(
                record, scaled, services.profile,
                reset_component=services.reset_component,
                reset_drive_state=services.reset_drive_state)

    if struct.unpack_from('<i', record, 0x464)[0] == services.designated_mode:
        services.designated_mode_action()
        cursor_reset_action(
            enabled=services.mouse_controller_enabled,
            initialized=services.mouse_controller_initialized,
            input_mode=services.mouse_input_mode,
            environment_mode=services.mouse_environment_mode,
            x=services.mouse_position_x, y=services.mouse_position_y,
            set_state=services.set_mouse_state)
    services.complete_interface_reset(1, record)

    return record


def reset_world_object(record, *, services):
    """Run the verified 0x43b750 pipeline through mapped path state.

    The remaining track-rate and virtual-interface tail is not hidden behind
    guessed behavior.
    """
    return reset_world_object_path_stage(record, services=services)
