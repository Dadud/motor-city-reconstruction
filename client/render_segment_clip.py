"""Renderer segment clipping recovered from the MCO homogeneous pipeline."""
from dataclasses import dataclass
import math
import struct

from .tire_response import f32


@dataclass(frozen=True)
class SegmentClipBounds:
    near_w: float
    far_w: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    xy_mask: int

    def __post_init__(self):
        for name in ('near_w', 'far_w', 'x_min', 'x_max', 'y_min', 'y_max'):
            try:
                value=f32(getattr(self,name))
            except (TypeError, ValueError) as exc:
                raise ValueError('clip bounds must be finite float32 values') from exc
            object.__setattr__(self,name,value)
        if type(self.xy_mask) is not int or not 0 <= self.xy_mask <= 0xff:
            raise ValueError('XY clip mask must be a byte')


def _interpolate(a, b, ratio):
    return f32(a - (a - b) * ratio)


def _interpolate_second(value, first_value, ratio):
    return f32(value - (first_value - value) * ratio)


def _depth_intersection(point, other, plane, depth, *, second=False):
    denominator=(other[3]-point[3] if second else point[3]-other[3])
    ratio=(point[3] - plane) / denominator
    interpolate=(_interpolate_second if second else _interpolate)
    point[0]=interpolate(point[0],other[0],ratio)
    point[1]=interpolate(point[1],other[1],ratio)
    point[2]=f32(depth)
    point[3]=f32(plane)


def _refresh_xy_code(point, code, bounds):
    x,y=point[0],point[1]
    if bounds.y_min <= y <= bounds.y_max:
        code &= 0xf3
    elif y > bounds.y_max:
        code=(code & 0xfb) | 0x08
    else:
        code=(code & 0xf7) | 0x04
    if bounds.x_min <= x <= bounds.x_max:
        code &= 0xcf
    elif x > bounds.x_max:
        code=(code & 0xef) | 0x20
    else:
        code=(code & 0xdf) | 0x10
    return code


def clip_render_segment(first, second, first_code, second_code, bounds):
    """Return the clipped six-float endpoints, or ``None`` when rejected.

    The input codes and limits are renderer state supplied by the caller.
    ``None`` represents the original function's early return without invoking
    its global segment callback.
    """
    if (len(first) != 6 or len(second) != 6 or
        any(not math.isfinite(value) for value in (*first,*second))):
        raise ValueError('render segments require two finite six-float vertices')
    if any(type(code) is not int or not 0 <= code <= 0xff
           for code in (first_code,second_code)):
        raise ValueError('clip codes must be bytes')
    if not isinstance(bounds,SegmentClipBounds):
        raise TypeError('bounds must be SegmentClipBounds')

    a=[f32(value) for value in first]
    b=[f32(value) for value in second]
    ca,cb=first_code,second_code
    if ca & cb:
        return None
    if ca == 0 and cb == 0:
        return tuple(a),tuple(b)

    if ca & 0x01:
        _depth_intersection(a,b,bounds.near_w,0.0)
        ca=_refresh_xy_code(a,ca,bounds)
        if ca & cb:
            return None
    if cb & 0x01:
        _depth_intersection(b,a,bounds.near_w,0.0,second=True)
        cb=_refresh_xy_code(b,cb,bounds)
        if cb & ca:
            return None
    if ca & 0x02:
        _depth_intersection(a,b,bounds.far_w,1.0)
        ca=_refresh_xy_code(a,ca,bounds)
        if ca & cb:
            return None
    if cb & 0x02:
        _depth_intersection(b,a,bounds.far_w,1.0,second=True)
        cb=_refresh_xy_code(b,cb,bounds)
        if cb & ca:
            return None

    if ca & 0x30:
        plane=(bounds.x_min if ca & 0x10 else bounds.x_max)
        ratio=(a[0]-plane)/(a[0]-b[0])
        a[1]=_interpolate(a[1],b[1],ratio)
        a[0]=f32(plane)
        ca &= bounds.xy_mask
        if a[1] >= bounds.y_min:
            if a[1] > bounds.y_max:
                ca |= 0x08
        else:
            ca |= 0x04
        if ca & cb:
            return None
    if cb & 0x30:
        plane=(bounds.x_min if cb & 0x10 else bounds.x_max)
        ratio=(b[0]-plane)/(a[0]-b[0])
        b[1]=_interpolate_second(b[1],a[1],ratio)
        b[0]=f32(plane)
        cb &= bounds.xy_mask
        if b[1] >= bounds.y_min:
            if b[1] > bounds.y_max:
                cb |= 0x08
        else:
            cb |= 0x04
        if cb & ca:
            return None

    if ca & 0x0c:
        plane=(bounds.y_min if ca & 0x04 else bounds.y_max)
        ratio=(a[1]-plane)/(a[1]-b[1])
        a[0]=_interpolate(a[0],b[0],ratio)
        a[1]=f32(plane)
    if cb & 0x0c:
        plane=(bounds.y_min if cb & 0x04 else bounds.y_max)
        ratio=(b[1]-plane)/(a[1]-b[1])
        b[0]=_interpolate_second(b[0],a[0],ratio)
        b[1]=f32(plane)
    return tuple(a),tuple(b)
