"""Mouse state getter branches with portable scalar global views."""
from __future__ import annotations
from dataclasses import dataclass
import struct

from .mouse_controller import clamp_i32
from .input_device_state import read_input_device_state


@dataclass(frozen=True)
class MouseScalarState:
    access_mode: int
    state8: int
    state9: int


@dataclass
class MouseAboutState:
    """Static device-information buffer and diagnostic globals."""

    initialized: int
    information: bytearray
    diagnostic_file: int = 0
    diagnostic_line: int = 0


MOUSE_SOURCE_FILE = 0x84A004
MOUSE_ABOUT_ERROR = 0x84A0A8
MOUSE_INVALID_GETSTATE = 0x84A088


def get_mouse_about_state(state, *, query_device_info, report_error):
    """Port selector 2 of 0x6efcd0 around the DirectInput info provider.

    The device-information helper supplies a status and writes the shared
    0x21c-byte image. A nonzero status returns null without logging. If the
    device was never initialized, the original reports its fixed diagnostic.
    """
    if not isinstance(state, MouseAboutState):
        raise ValueError('MouseAboutState is required')
    if type(state.initialized) is not int or not 0 <= state.initialized <= 0xffffffff:
        raise ValueError('mouse initialization flag must be uint32')
    if not isinstance(state.information, bytearray) or len(state.information) < 0x21c:
        raise ValueError('mouse information buffer must contain 0x21c bytes')
    if not callable(query_device_info) or not callable(report_error):
        raise ValueError('device-info and diagnostic services are required')

    if state.initialized != 0:
        status = query_device_info(state.information)
        if type(status) is not int or not 0 <= status <= 0xffffffff:
            raise ValueError('device-info status must be uint32')
        return state.information if status == 0 else None

    state.diagnostic_file = MOUSE_SOURCE_FILE
    state.diagnostic_line = 0x24a
    report_error(MOUSE_ABOUT_ERROR)
    return None


def get_mouse_invalid_state(state, *, report_error):
    """Port the invalid-selector default branch of 0x6efcd0."""
    if not isinstance(state, MouseAboutState):
        raise ValueError('MouseAboutState is required for diagnostic globals')
    if not callable(report_error):
        raise ValueError('diagnostic service is required')
    state.diagnostic_file = MOUSE_SOURCE_FILE
    state.diagnostic_line = 0x256
    report_error(MOUSE_INVALID_GETSTATE)
    return None


@dataclass
class MouseGetStateContext:
    about: MouseAboutState
    cursor: MouseCursorGlobals
    scalar: MouseScalarState


def get_mouse_state(selector, context, *, query_device_info,
                    query_absolute_cursor, ensure_device_acquired,
                    read_device_state, report_error):
    """Translate the complete selector dispatch of 0x6efcd0.

    The surrounding host owns DirectInput and cursor-position acquisition;
    the native routine's state transformations and diagnostic selection are
    performed by the called source branches.
    """
    if not isinstance(context, MouseGetStateContext):
        raise ValueError('MouseGetStateContext is required')
    if type(selector) is not int or not 0 <= selector <= 0xffffffff:
        raise ValueError('mouse state selector must be uint32')
    if selector == 2:
        return get_mouse_about_state(
            context.about, query_device_info=query_device_info,
            report_error=report_error)
    if selector == 6:
        if context.cursor.access_mode == 4:
            if not callable(query_absolute_cursor):
                raise ValueError('absolute cursor query is required')
            button_state, x, y = query_absolute_cursor()
            return get_mouse_cursor_state_absolute(
                context.cursor, button_state=button_state,
                cursor_x=x, cursor_y=y)
        output = bytearray(16)
        read_input_device_state(
            context.cursor.device, output, len(output),
            ensure_acquired=ensure_device_acquired,
            get_state=read_device_state)
        return get_mouse_cursor_state_direct_input(
            context.cursor, output)
    if selector in (7, 8, 9):
        return get_mouse_scalar_state(selector, context.scalar)
    return get_mouse_invalid_state(context.about, report_error=report_error)


@dataclass
class MouseCursorGlobals:
    """Mutable cursor-mode state corresponding to 0xb3620c..0xb36238."""

    access_mode: int
    clamp_wheel: int
    x: int
    y: int
    z: int
    minimum_z: int
    maximum_z: int
    wheel_delta: int
    button0: int = 0
    button1: int = 0
    button2: int = 0
    auxiliary_button: int = 0
    minimum_x: int = -(1 << 31)
    maximum_x: int = (1 << 31) - 1
    minimum_y: int = -(1 << 31)
    maximum_y: int = (1 << 31) - 1
    position_mode: int = 0
    device: int = 0


def get_mouse_cursor_state_absolute(state, *, button_state, cursor_x, cursor_y):
    """Port selector 6 of 0x6efcd0 when access mode is four.

    The cursor query values are the outputs of child 0x6f07a0. The returned
    object is the bounded host view of the original global POINT/button record.
    DirectInput access-mode behavior remains a separate branch.
    """
    if not isinstance(state, MouseCursorGlobals):
        raise ValueError('MouseCursorGlobals is required')
    if state.access_mode != 4:
        raise NotImplementedError('selector 6 DirectInput mode is not ported')
    for value in (state.x, state.y, state.z, state.minimum_z, state.maximum_z,
                  state.wheel_delta, cursor_x, cursor_y):
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise ValueError('cursor and wheel values must be signed int32')
    if type(state.clamp_wheel) is not int or state.clamp_wheel not in (0, 1):
        raise ValueError('wheel clamp mode must be zero or one')
    if type(button_state) is not int or not 0 <= button_state <= 0xffffffff:
        raise ValueError('button state must be uint32')

    state.x = cursor_x
    state.y = cursor_y
    wheel_position = (state.z + state.wheel_delta) & 0xffffffff
    if wheel_position & 0x80000000:
        wheel_position -= 1 << 32
    if state.clamp_wheel:
        state.z = clamp_i32(wheel_position, state.minimum_z, state.maximum_z)
    else:
        state.z = wheel_position
    state.wheel_delta = 0
    state.auxiliary_button = 0
    state.button0 = 0x70 if button_state & 1 else 0
    state.button1 = 0x70 if button_state & 2 else 0
    state.button2 = 0x70 if button_state & 4 else 0
    return state


def get_mouse_cursor_state_direct_input(state, device_state):
    """Port selector 6 of 0x6efcd0 outside absolute cursor mode.

    ``device_state`` is the 16-byte result image written by DirectInput child
    0x6f0a30. Its return status is ignored by the original caller; therefore
    callers supply the resulting bytes, including unchanged bytes on failure.
    """
    if not isinstance(state, MouseCursorGlobals):
        raise ValueError('MouseCursorGlobals is required')
    if state.access_mode == 4:
        raise NotImplementedError('absolute cursor mode uses another branch')
    if not isinstance(device_state, (bytes, bytearray, memoryview)) \
            or len(device_state) < 16:
        raise ValueError('DirectInput state must contain the 16-byte sample')
    bounds = (state.minimum_x, state.maximum_x,
              state.minimum_y, state.maximum_y,
              state.minimum_z, state.maximum_z)
    for value in (state.x, state.y, state.z, *bounds):
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise ValueError('cursor coordinates and bounds must be signed int32')

    dx, dy, dz = struct.unpack_from('<3i', device_state)
    if state.position_mode == 3:
        state.x, state.y, state.z = dx, dy, dz
    elif not state.clamp_wheel:
        state.x = _wrap_i32(state.x + dx)
        state.y = _wrap_i32(state.y + dy)
        state.z = _wrap_i32(state.z + dz)
    else:
        state.x = clamp_i32(_wrap_i32(state.x + dx),
                            state.minimum_x, state.maximum_x)
        state.y = clamp_i32(_wrap_i32(state.y + dy),
                            state.minimum_y, state.maximum_y)
        state.z = clamp_i32(_wrap_i32(state.z + dz),
                            state.minimum_z, state.maximum_z)
    state.button0, state.button1, state.button2, state.auxiliary_button = \
        memoryview(device_state)[12:16]
    return state


def _wrap_i32(value):
    value &= 0xffffffff
    return value - (1 << 32) if value & 0x80000000 else value


def get_mouse_scalar_state(selector, state):
    """Port selectors 7, 8 and 9 of 0x6efcd0.

    The remaining getter selectors perform DirectInput, cursor, diagnostic or
    button-state work and are intentionally not represented by this scalar API.
    """
    if not isinstance(state, MouseScalarState):
        raise ValueError('MouseScalarState is required')
    if type(selector) is not int or not 0 <= selector <= 0xffffffff:
        raise ValueError('mouse state selector must be uint32')
    if selector == 7:
        return state.access_mode
    if selector == 8:
        return state.state8
    if selector == 9:
        return state.state9
    raise NotImplementedError('only scalar mouse getter selectors 7, 8, 9 are ported')
