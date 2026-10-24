"""Border-rectangle command geometry recovered from the MCO UI renderer."""
from dataclasses import dataclass

from .render_clip_code import RenderClipBounds
from .render_segment_clip import SegmentClipBounds
from .render_segment_construct import (RenderSegmentResult,
                                       construct_render_segment)
from .render_clip_code import render_clip_code


def _signed32(value):
    value &= 0xffffffff
    return value if value < 0x80000000 else value-(1<<32)


@dataclass(frozen=True)
class RenderRectangleEdge:
    x1: int
    y1: int
    x2: int
    y2: int
    attribute1: int
    attribute2: int


@dataclass(frozen=True)
class RenderRectangleVertex:
    x_word: int
    y_word: int
    z_word: int
    w_word: int
    attribute_word: int
    clip_tail_words: tuple
    clip_code: int


def plan_filled_rectangle_vertices(x,y,width,height,attributes,
                                   clip_code_bounds,*,opaque_words):
    """Translate 0x482700's vertex setup and clip-code stage.

    The original creates TL, TR, BR, BL records, then invokes 0x6cb810 on
    each. Uninitialized sixth words are explicit caller-provided residue.
    The subsequent polygon dispatcher 0x474ee0 is not included.
    """
    if any(type(value) is not int or not -0x80000000<=value<=0x7fffffff
           for value in (x,y,width,height)):
        raise ValueError('rectangle geometry must use signed 32-bit integers')
    if not isinstance(attributes,(tuple,list)) or len(attributes)!=4 or any(
        type(value) is not int or not 0<=value<=0xffffffff
        for value in attributes):
        raise ValueError('filled rectangle requires four raw attribute words')
    if not isinstance(opaque_words,(tuple,list)) or len(opaque_words)!=4 or any(
        not isinstance(pair,(tuple,list)) or len(pair)!=3 or any(
            type(value) is not int or not 0<=value<=0xffffffff for value in pair)
        for pair in opaque_words):
        raise ValueError('four explicit triples of untouched stack words are required')
    from .render_clip_code import RenderClipBounds
    if not isinstance(clip_code_bounds,RenderClipBounds):
        raise TypeError('clip_code_bounds must be RenderClipBounds')

    right=_signed32(x+width)
    bottom=_signed32(y+height)
    corners=((x,y),(right,y),(right,bottom),(x,bottom))
    vertices=[]
    for (vx,vy),attribute,residue in zip(corners,attributes,opaque_words):
        words=(_float_word(vx),_float_word(vy),0x3f7fff00,0x37800080,
               attribute)
        code=render_clip_code(tuple(_signed32(word) for word in words[:4]),
                              clip_code_bounds)
        # 0x6cb810 writes one byte at the start of a 12-byte tail.
        clip_word=(residue[0]&0xffffff00)|code
        vertices.append(RenderRectangleVertex(
            *words,(clip_word,residue[1],residue[2]),code))
    return tuple(vertices)


def _float_word(value):
    import struct
    try:
        return struct.unpack('<I',struct.pack('<f',float(value)))[0]
    except OverflowError:
        return 0xff800000 if value < 0 else 0x7f800000


def plan_rectangle_border_edges(x,y,width,height,inset,colors):
    """Translate 0x47faf0's non-filled four-edge branch.

    Coordinates and extents are integer client-space values. Arithmetic wraps
    as signed x86 32-bit operations. The function returns no edges when both
    extents are zero, matching the caller's pre-inset empty-rectangle gate.
    """
    if any(type(value) is not int or not -0x80000000<=value<=0x7fffffff
           for value in (x,y,width,height,inset)):
        raise ValueError('rectangle geometry must use signed 32-bit integers')
    if not isinstance(colors,(tuple,list)) or len(colors)!=4 or any(
        type(value) is not int or not 0<=value<=0xffffffff for value in colors):
        raise ValueError('rectangle border requires four raw attribute words')
    if width==0 and height==0:
        return ()
    inner_width=_signed32(width-inset)
    inner_height=_signed32(height-inset)
    right=_signed32(x+inner_width)
    bottom=_signed32(y+inner_height)
    first,second,third,fourth=colors
    return (
        RenderRectangleEdge(x,y,right,y,first,second),
        RenderRectangleEdge(right,y,right,bottom,second,third),
        RenderRectangleEdge(right,bottom,x,bottom,third,fourth),
        RenderRectangleEdge(x,bottom,x,y,fourth,first),
    )


def construct_rectangle_border(x,y,width,height,inset,colors,
                               clip_code_bounds,segment_bounds,*,opaque_words):
    """Compose the rectangle edges with the recovered native segment path.

    Four explicit stack-residue pairs represent the untouched words in the
    four calls to 0x482610. Returned records are the events sent to the draw
    callback; device effects remain external.
    """
    if not isinstance(opaque_words,(tuple,list)) or len(opaque_words)!=4:
        raise ValueError('rectangle construction requires four opaque-word pairs')
    edges=plan_rectangle_border_edges(x,y,width,height,inset,colors)
    if not edges:
        return ()
    if not isinstance(clip_code_bounds,RenderClipBounds):
        raise TypeError('clip_code_bounds must be RenderClipBounds')
    if not isinstance(segment_bounds,SegmentClipBounds):
        raise TypeError('segment_bounds must be SegmentClipBounds')
    results=[]
    for edge,residue in zip(edges,opaque_words):
        results.append(construct_render_segment(
            edge.x1,edge.y1,edge.x2,edge.y2,edge.attribute1,edge.attribute2,
            clip_code_bounds,segment_bounds,opaque_words=residue))
    return tuple(results)
