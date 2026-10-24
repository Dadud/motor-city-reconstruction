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


@dataclass(frozen=True)
class RenderViewportRequest:
    surface_width: int
    surface_height: int
    x: int
    y: int
    width: int
    height: int
    alternate_path: bool = False
    client_width: int = 0
    client_height: int = 0


@dataclass(frozen=True)
class RenderViewportRequestResult:
    x_min: int
    y_min: int
    x_end: int
    y_end: int
    clamped_width: int
    clamped_height: int
    callback_args: tuple
    viewport_state: object = None
    alternate_bounds: object = None
    globals_by_address: dict = None


def _signed32(value):
    value &= 0xffffffff
    return value if value < 0x80000000 else value - 0x100000000


def prepare_render_viewport_request(request, *, query_client_rect=False):
    """Translate 0x5668c0 with OS/device callbacks supplied as explicit data.

    The device callback's input tuple is returned as an event. When requested,
    the observed client rectangle is supplied by `request.client_width/height`;
    obtaining the real HWND and calling Win32 remain outside this function.
    """
    if not isinstance(request,RenderViewportRequest):
        raise TypeError('request must be RenderViewportRequest')
    if any(type(value) is not int for value in
           (request.surface_width,request.surface_height,request.x,request.y,
            request.width,request.height,request.client_width,request.client_height)):
        raise ValueError('viewport request fields must be integers')
    if not 1 <= request.surface_width <= 0x7fffffff or not 1 <= request.surface_height <= 0x7fffffff:
        raise ValueError('surface dimensions must be positive signed 32-bit values')
    if any(not -0x80000000 <= value <= 0xffffffff for value in
           (request.x,request.y)) or any(
           not -0x80000000 <= value <= 0x7fffffff for value in
           (request.width,request.height)):
        raise ValueError('viewport coordinates and extents are outside 32-bit values')
    if query_client_rect and (request.client_width < 0 or request.client_height < 0):
        raise ValueError('client dimensions cannot be negative')

    x=max(_signed32(request.x),0)
    y=max(_signed32(request.y),0)
    x=min(x,request.surface_width-1)
    y=min(y,request.surface_height-1)
    width=request.width
    height=request.height
    remaining_x=_signed32(request.surface_width-x)
    remaining_y=_signed32(request.surface_height-y)
    if remaining_x <= width:
        width=remaining_x
    if remaining_y <= height:
        height=remaining_y
    x_end=request.surface_width
    sum_x=_signed32(x+width)
    if sum_x < request.surface_width:
        x_end=sum_x
    y_end=request.surface_height
    sum_y=_signed32(y+height)
    if sum_y < request.surface_height:
        y_end=sum_y
    x_min=x if x >= 1 else 0
    y_min=y if y >= 1 else 0
    if query_client_rect:
        x_end=min(x_end,request.client_width)
        y_end=min(y_end,request.client_height)

    callback_args=(x_min,y_min,x_end,y_end)
    if request.alternate_path:
        x0=f32(x_min)
        y0=f32(y_min)
        x1=f32(x0+f32(_signed32(x_end-x_min)))
        y1=f32(y0+f32(_signed32(y_end-y_min)))
        bounds=set_alternate_render_bounds(x0,y0,f32(x_end),f32(y_end))
        globals_by_address={
            0x00aa43c0:x,0x00aa43c4:y,
            0x00aa43c8:width,0x00aa43cc:height,
            0x00b31fc0:y0,0x00b31fbc:x0,
            0x008c672c:x1,0x008c6730:y1,
            0x00b424a0:y1,0x00b424a8:x1,0x00b424ac:y1,
            0x00b424b4:x1,0x00b424c0:y0,0x00b424c4:x0,
            **bounds.globals_by_address(),
        }
        return RenderViewportRequestResult(
            x_min,y_min,x_end,y_end,width,height,callback_args,
            alternate_bounds=bounds,globals_by_address=globals_by_address)

    viewport=RenderViewport(f32(x_min),f32(y_min),
                            f32(_signed32(x_end-x_min)),
                            f32(_signed32(y_end-y_min)),10.0,
                            0.0016666667070239782)
    records=[bytearray(32) for _ in range(100)]
    state=configure_render_viewport(viewport,records)
    globals_by_address=state.globals_by_address()
    globals_by_address.update({
        0x00aa43c0:x,0x00aa43c4:y,
        0x00aa43c8:width,0x00aa43cc:height,
        0x00993848:f32(x_min),0x009938b0:f32(x_end),
        0x009938ac:f32(y_min),0x00993bb0:f32(y_end),
        0x0099248c:f32(x_min),0x00993840:f32(x_end),
        0x00993a48:f32(y_min),0x00993bb4:f32(y_end),
        0x00993844:f32(0.0016666667070239782),
        0x00992488:f32(10.0),
        0x00993a4c:f32(0.0016666667070239782),
        0x009938a8:f32(10.0),
    })
    return RenderViewportRequestResult(
        x_min,y_min,x_end,y_end,width,height,callback_args,
        viewport_state=state,globals_by_address=globals_by_address)


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
