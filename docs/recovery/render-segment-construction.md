# Render segment construction

`0x482610` builds two six-word endpoints from integer screen coordinates. It
stores binary32 X/Y, fixed Z/W words `0x3f7fff00` and `0x37800080`, and the two
raw caller attributes. The last word of each endpoint is read from an untouched
stack slot, so it remains an explicit input in the reconstruction. The routine
then computes both clip codes, runs `0x6cb970`, and dispatches the resulting
endpoints through the renderer callback when the segment survives. The Python
result records that callback payload instead of performing device work.

`client/render_segment_construct.py::construct_render_segment` composes the
existing clip-code and segment-clipping translations while preserving raw
attribute bits. Five hundred twelve direct original calls match the callback
records across pass-through, clipped and rejected segments. The oracle supplies
the original uninitialized stack words, renderer bounds, and a controlled
draw callback. IEEE divide-by-zero behavior in parallel clipping cases is kept
as binary32 infinity/NaN, rather than raising a Python exception.

The Ghidra dossier is REA Evidence
`ev_85261f5efc9d42bddd423daeabe08e35c79e45b556236c4514f9491ee229d8b3`.
