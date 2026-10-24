# Renderer segment clipping

`0x6cb970` clips two six-float endpoints through the configured near/far and
X/Y planes. It rejects a segment when both endpoint outcodes share a bit,
passes fully-inside endpoints directly to the renderer callback, and sends
accepted clipped endpoints through the selected callback. This translation
returns the callback's endpoint data while leaving the device callback itself
as a caller-owned effect.

`client/render_segment_clip.py::clip_render_segment` follows the original plane
order and outcode updates. 512 deterministic endpoint pairs matched direct
execution of the installed function bit-for-bit; the native callback arguments
were captured with a controlled stub. Plane limits, their runtime producers,
and the callback's rendering side effects remain separate dependencies.

REA Evidence `ev_c5211d45205e891adf12a0bfed0f621f83297bcaf3e2298cdc1e6b96f854be95`
contains the complete Ghidra function dossier. Its indirect callback dispatcher
is separately observed in `ev_31d6c6456a2dd4a061f50fe475bd317121b1b8a11cfd7d8a89f20e2225923dc2`.
