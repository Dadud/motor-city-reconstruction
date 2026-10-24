"""Bounded polygon clipping decisions recovered from the MCO renderer."""
import struct


def reject_triangle_on_shared_near_plane(clip_codes, plane_mask=0x01):
    """Return the native empty-polygon sentinel for a shared near-plane bit.

    This is the first pass in 0x475de0: with plane bit 0 active, three
    vertices all outside that plane contribute no retained vertices or
    intersections, so the routine returns ``0xffffffff``. Other masks and
    partially retained polygons are outside this translation.
    """
    if (not isinstance(clip_codes,(tuple,list)) or len(clip_codes)!=3 or
        any(type(code) is not int or not 0<=code<=0xff
            for code in clip_codes)):
        raise ValueError('polygon clipping requires three byte clip codes')
    if type(plane_mask) is not int or not 0<=plane_mask<=0xff:
        raise ValueError('polygon clip mask must be a byte')
    if plane_mask!=0x01:
        raise ValueError('only the near-plane pass is translated')
    if all(code&plane_mask for code in clip_codes):
        return 0xffffffff
    return None


def _f32(value):
    try:
        return struct.unpack('<f',struct.pack('<f',value))[0]
    except OverflowError:
        return float('-inf') if value<0 else float('inf')


def _word_float(word):
    return struct.unpack('<f',struct.pack('<I',word))[0]


def _float_word(value):
    return struct.unpack('<I',struct.pack('<f',_f32(value)))[0]


def _prepare_triangle(vertex_records):
    colors=tuple(record[4] for record in vertex_records)
    vary_alpha=len({color>>24 for color in colors})>1
    vary_rgb=len({color&0xffffff for color in colors})>1
    vary_color=len(set(colors))>1
    transformed=[]
    for record in vertex_records:
        w=_word_float(record[3])
        color=record[4]
        transformed.append([
            _word_float(record[0]),_word_float(record[1]),0.0,w,
            _f32(_word_float(record[6])*w),
            _f32(_word_float(record[7])*w),
            float((color>>24)&0xff),float((color>>16)&0xff),
            float((color>>8)&0xff),float(color&0xff),
        ])
    return transformed,vary_alpha,vary_rgb,vary_color


def _interpolate_edge(a,b,t,vary_alpha,vary_rgb,vary_color):
    intersection=[0.0]*10
    for field in (0,1,3,4,5):
        intersection[field]=_f32(a[field]-(a[field]-b[field])*t)
    if vary_color:
        for field in range(6,10):
            if field==6 and not vary_alpha:
                intersection[field]=a[field]
            elif field>=7 and not vary_rgb:
                intersection[field]=a[field]
            else:
                intersection[field]=_f32(a[field]-(a[field]-b[field])*t)
    else:
        intersection[6:10]=a[6:10]
    return intersection


def _pack_clipped_polygon(output,near_w,far_value):
    callback_vertices=[]
    for vertex in output:
        x,y,w=vertex[0],vertex[1],vertex[3]
        depth=(_f32(near_w-w) if w>=0 and w<=near_w else far_value)
        channels=[int(round(vertex[index]))&0xff for index in (6,7,8,9)]
        color=(channels[0]<<24)|(channels[1]<<16)|(channels[2]<<8)|channels[3]
        if w==0:
            u=v=float('inf')
        else:
            reciprocal=_f32(near_w/w)
            u=_f32(reciprocal*vertex[4])
            v=_f32(reciprocal*vertex[5])
        words=(_float_word(x),_float_word(y),_float_word(depth),
               _float_word(w),color,0,_float_word(u),_float_word(v))
        if any((word|0x80000000)==0xffc00000 for word in words[:4]):
            continue
        callback_vertices.append(words)
    if len(callback_vertices)<3:
        return 0xffffffff,()
    return len(callback_vertices)-2,tuple(callback_vertices)


def clip_triangle_near_plane(clip_codes, vertex_records, *,
                             plane_w, near_w=1.0, far_w=0.0):
    """Clip one triangle against W=plane_w and pack the draw-trifan records.

    Supported domain: exactly one of three vertices has near-plane outcode
    bit 0 set, all other clipping planes are disabled, all three input records
    have ten raw words, and the resulting polygon contains finite values.
    The return value matches the callback's ``(triangle_count, vertices)``;
    the callback receives ``vertex_count - 2`` as its first argument.
    """
    if (not isinstance(clip_codes,(tuple,list)) or len(clip_codes)!=3 or
        any(type(code) is not int or not 0<=code<=0xff
            for code in clip_codes)):
        raise ValueError('near clipping requires three byte clip codes')
    if (not isinstance(vertex_records,(tuple,list)) or len(vertex_records)!=3 or
        any(not isinstance(record,(tuple,list)) or len(record)!=10 or any(
            type(word) is not int or not 0<=word<=0xffffffff
            for word in record) for record in vertex_records)):
        raise ValueError('near clipping requires three ten-word vertices')
    flags=tuple(code&1 for code in clip_codes)
    if sum(flags)!=1:
        raise ValueError('exactly one vertex must be outside the near plane')
    if any(code&0xfe for code in clip_codes):
        raise ValueError('other clip planes must be inactive')
    plane_w=_f32(float(plane_w))
    near_w=_f32(float(near_w))
    far_value=_f32(float(far_w))

    transformed,vary_alpha,vary_rgb,vary_color=_prepare_triangle(vertex_records)

    output=[]
    current=2
    previous=0
    for _ in range(3):
        current_inside=not flags[current]
        if current_inside:
            output.append(transformed[current])
        if flags[current]!=flags[previous]:
            a=transformed[current]
            b=transformed[previous]
            # x87 keeps the subtraction/division intermediates extended;
            # only the assigned parameter word is rounded to binary32.
            delta_w=a[3]-b[3]
            if delta_w==0:
                raise ValueError('near-plane crossing has a zero W denominator')
            reciprocal=near_w/delta_w
            t=_f32((a[3]-plane_w)*reciprocal)
            if t>near_w or t<far_value:
                t=_f32(reciprocal*a[3])
            intersection=_interpolate_edge(
                a,b,t,vary_alpha,vary_rgb,vary_color)
            intersection[3]=plane_w
            output.append(intersection)
        current,previous=previous,(previous+1)%3

    return _pack_clipped_polygon(output,near_w,far_value)


def clip_triangle_y_max_plane(clip_codes, vertex_records, *,
                              y_max, near_w=1.0, far_w=0.0):
    """Clip one triangle against the upper-Y plane (clip-code bit 0x08).

    This isolates the single top-plane pass in 0x475de0. Near-W and every
    other plane must be inactive; exactly one input vertex must be above
    ``y_max``. Returns the draw-trifan triangle count and eight-word vertices.
    """
    if (not isinstance(clip_codes,(tuple,list)) or len(clip_codes)!=3 or
        any(type(code) is not int or not 0<=code<=0xff for code in clip_codes)):
        raise ValueError('Y clipping requires three byte clip codes')
    if (not isinstance(vertex_records,(tuple,list)) or len(vertex_records)!=3 or
        any(not isinstance(record,(tuple,list)) or len(record)!=10 or any(
            type(word) is not int or not 0<=word<=0xffffffff
            for word in record) for record in vertex_records)):
        raise ValueError('Y clipping requires three ten-word vertices')
    flags=tuple(code&0x08 for code in clip_codes)
    if sum(bool(flag) for flag in flags)!=1:
        raise ValueError('exactly one vertex must be outside the upper-Y plane')
    if any(code&0xf7 for code in clip_codes):
        raise ValueError('other clip planes must be inactive')
    y_max=_f32(float(y_max))
    near_w=_f32(float(near_w))
    far_value=_f32(float(far_w))
    transformed,vary_alpha,vary_rgb,vary_color=_prepare_triangle(vertex_records)

    output=[]
    current=2
    previous=0
    for _ in range(3):
        current_inside=not flags[current]
        if current_inside:
            output.append(transformed[current])
        if flags[current]!=flags[previous]:
            a=transformed[current]
            b=transformed[previous]
            delta_y=a[1]-b[1]
            if delta_y==0:
                raise ValueError('Y-plane crossing has a zero denominator')
            t=_f32((a[1]-y_max)/delta_y)
            intersection=_interpolate_edge(
                a,b,t,vary_alpha,vary_rgb,vary_color)
            intersection[1]=y_max
            output.append(intersection)
        current,previous=previous,(previous+1)%3
    return _pack_clipped_polygon(output,near_w,far_value)


def clip_triangle_y_min_plane(clip_codes, vertex_records, *,
                              y_min, near_w=1.0, far_w=0.0):
    """Clip one triangle against the lower-Y plane (clip-code bit 0x04)."""
    if (not isinstance(clip_codes,(tuple,list)) or len(clip_codes)!=3 or
        any(type(code) is not int or not 0<=code<=0xff for code in clip_codes)):
        raise ValueError('Y clipping requires three byte clip codes')
    if (not isinstance(vertex_records,(tuple,list)) or len(vertex_records)!=3 or
        any(not isinstance(record,(tuple,list)) or len(record)!=10 or any(
            type(word) is not int or not 0<=word<=0xffffffff
            for word in record) for record in vertex_records)):
        raise ValueError('Y clipping requires three ten-word vertices')
    flags=tuple(code&0x04 for code in clip_codes)
    if sum(bool(flag) for flag in flags)!=1:
        raise ValueError('exactly one vertex must be outside the lower-Y plane')
    if any(code&0xfb for code in clip_codes):
        raise ValueError('other clip planes must be inactive')
    y_min=_f32(float(y_min))
    near_w=_f32(float(near_w))
    far_value=_f32(float(far_w))
    transformed,vary_alpha,vary_rgb,vary_color=_prepare_triangle(vertex_records)

    output=[]
    current=2
    previous=0
    for _ in range(3):
        current_inside=not flags[current]
        if current_inside:
            output.append(transformed[current])
        if flags[current]!=flags[previous]:
            a=transformed[current]
            b=transformed[previous]
            delta_y=a[1]-b[1]
            if delta_y==0:
                raise ValueError('Y-plane crossing has a zero denominator')
            t=_f32((a[1]-y_min)/delta_y)
            intersection=_interpolate_edge(
                a,b,t,vary_alpha,vary_rgb,vary_color)
            intersection[1]=y_min
            output.append(intersection)
        current,previous=previous,(previous+1)%3
    return _pack_clipped_polygon(output,near_w,far_value)
