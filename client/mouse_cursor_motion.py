"""Cursor-centering and signed-axis response from the 0x4ad6f0 prelude."""
from dataclasses import dataclass
import math
import struct

from .mouse_controller import clamp_i32


@dataclass(frozen=True)
class MouseCursorMotionParameters:
    center: int
    radius: float
    deadzone: float
    secondary_target: int
    center_frames_remaining: int


@dataclass(frozen=True)
class MouseCursorMotionResult:
    sample: int
    clamped_sample: int
    signed_axis: int
    center_frames_remaining: int
    setter_calls: tuple


def _float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _wrap_i32(value):
    value &= 0xffffffff
    return value - (1 << 32) if value & 0x80000000 else value


def update_mouse_cursor_motion(sample, parameters):
    """Translate the native bounds, center timer, and deadzone-to-axis math.

    This is the finite controller domain used by the shipped mouse loop:
    positive radius, nonnegative deadzone smaller than the radius, finite
    binary32 values, and signed 32-bit cursor/global words. Setter calls remain
    explicit because they update the shared cursor API and may have side effects.
    """
    if not isinstance(parameters, MouseCursorMotionParameters):
        raise ValueError('MouseCursorMotionParameters is required')
    if type(sample) is not int or not -(1 << 31) <= sample < (1 << 31):
        raise ValueError('cursor sample must be signed int32')
    for value in (parameters.center, parameters.secondary_target,
                  parameters.center_frames_remaining):
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            raise ValueError('cursor globals must be signed int32')
    radius = _float32(parameters.radius)
    deadzone = _float32(parameters.deadzone)
    if not math.isfinite(radius) or not math.isfinite(deadzone) \
            or radius <= deadzone or deadzone < 0:
        raise ValueError('mouse radius/deadzone must satisfy radius > deadzone >= 0')

    upper = math.trunc(parameters.center + radius)
    lower = math.trunc(parameters.center - radius)
    calls = ()
    if sample < lower or sample > upper:
        calls = ((3, sample), (4, parameters.secondary_target))
    clamped = clamp_i32(sample, lower, upper)

    distance = abs(clamped - parameters.center)
    ratio = _float32((distance - deadzone) / (radius - deadzone))
    if distance < deadzone:
        ratio = 0.0
    scale = 127.0 if sample > parameters.center else -127.0
    signed_axis = math.trunc(abs(ratio) * scale)
    signed_axis = clamp_i32(signed_axis, -127, 127)

    if clamped == parameters.center:
        remaining = _wrap_i32(parameters.center_frames_remaining - 1)
        if remaining < 0:
            remaining = 0
    else:
        remaining = 0x3c

    return MouseCursorMotionResult(sample, clamped, signed_axis,
                                   remaining, calls)
