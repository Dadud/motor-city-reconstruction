"""Renderer viewport and homogeneous clipping state recovered from MCO."""
from dataclasses import dataclass
import math
import struct

from .tire_response import f32


@dataclass(frozen=True)
class RenderViewport:
    x: float
    y: float
    width: float
    height: float
    w_plane_z0: float
    w_plane_z1: float


@dataclass(frozen=True)
class RenderViewportState:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    w_plane_z0: float
    w_plane_z1: float
    reciprocal_w_plane_z0: float
    reciprocal_depth_span: float

    def clip_code_bounds(self):
        """Project the viewport globals consumed by the integer clip helper."""
        from .render_clip_code import RenderClipBounds

        def signed_float_word(value):
            word=struct.unpack('<I',struct.pack('<f',value))[0]
            return word if word < 0x80000000 else word-(1<<32)

        return RenderClipBounds(
            signed_float_word(self.x_min),signed_float_word(self.x_max),
            signed_float_word(self.y_min),signed_float_word(self.y_max),
            signed_float_word(self.w_plane_z0),signed_float_word(1.0))

    def globals_by_address(self):
        """Expose values written by 0x6cb610, including aliased bounds."""
        return {
            0x008c672c:self.x_max,
            0x00b31fbc:self.x_min,
            0x00b31fc0:self.y_min,
            0x008c6730:self.y_max,
            0x00b424c8:self.w_plane_z1,
            0x00b424bc:self.w_plane_z0,
            0x00b424c4:self.x_min,
            0x00b424b8:self.w_plane_z1,
            0x00b31fc4:self.reciprocal_w_plane_z0,
            0x00b424c0:self.y_min,
            0x00b424b0:1.0,
            0x00b424a4:self.w_plane_z0,
            0x00b31fc8:self.reciprocal_depth_span,
            0x00b424a0:self.y_max,
            0x00b424a8:self.x_max,
            0x00b424ac:self.y_max,
            0x00b424b4:self.x_max,
        }


@dataclass(frozen=True)
class AlternateRenderBounds:
    """Bounds copied by the viewport caller's alternate rendering path."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def globals_by_address(self):
        return {
            0x00993848:self.x_min,
            0x009938b0:self.x_max,
            0x009938ac:self.y_min,
            0x00993bb0:self.y_max,
            0x0099248c:self.x_min,
            0x00993840:self.x_max,
            0x00993a48:self.y_min,
            0x00993bb4:self.y_max,
        }


def set_alternate_render_bounds(x_min, y_min, x_max, y_max):
    """Translate the eight global writes performed by native 0x474d00."""
    try:
        values=tuple(f32(value) for value in (x_min,y_min,x_max,y_max))
    except (TypeError,ValueError) as exc:
        raise ValueError('render bounds must be finite float32 values') from exc
    return AlternateRenderBounds(*values)


def classify_render_position(position, viewport_state):
    """Apply the original 0x6cb810 integer-word tests to float32 XYZW data."""
    if len(position) != 4 or any(not math.isfinite(value) for value in position):
        raise ValueError('render positions require four finite float values')
    words=struct.unpack('<4i',struct.pack('<4f',*position))
    from .render_clip_code import render_clip_code
    return render_clip_code(words,viewport_state.clip_code_bounds())


def configure_render_viewport(viewport, scratch_records):
    """Translate 0x6cb610, including its 100 strided scratch-field clears.

    `scratch_records` represents the original global table: exactly 100
    mutable 32-byte records, each with a cleared 32-bit field at offset 0x14.
    """
    if not isinstance(viewport,RenderViewport):
        raise TypeError('viewport must be RenderViewport')
    try:
        x,y,width,height,plane_z0,plane_z1=(f32(value) for value in
            (viewport.x,viewport.y,viewport.width,viewport.height,
             viewport.w_plane_z0,viewport.w_plane_z1))
    except (TypeError,ValueError) as exc:
        raise ValueError('viewport values must be finite float32 values') from exc
    if plane_z0 == 0.0 or plane_z1 == 0.0:
        raise ValueError('both W-plane parameters must be nonzero')
    if (not isinstance(scratch_records,(list,tuple)) or
        len(scratch_records) != 100 or
        any(not isinstance(record,bytearray) or len(record) != 32
            for record in scratch_records)):
        raise ValueError('scratch table requires 100 mutable 32-byte records')

    x_max=f32(x+width)
    y_max=f32(y+height)
    reciprocal_z0=f32(1.0/plane_z0)
    reciprocal_z1=1.0/plane_z1
    denominator=reciprocal_z1-reciprocal_z0
    if denominator == 0.0:
        raise ValueError('near/far reciprocal span must be nonzero')
    reciprocal_depth_span=f32(1.0/denominator)
    for record in scratch_records:
        struct.pack_into('<I',record,0x14,0)
    return RenderViewportState(x,y,x_max,y_max,plane_z0,plane_z1,
                               reciprocal_z0,reciprocal_depth_span)
