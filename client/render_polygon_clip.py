"""Bounded polygon clipping decisions recovered from the MCO renderer."""


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
