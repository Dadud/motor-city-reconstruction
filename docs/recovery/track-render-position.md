# Mode-8 track position callback

The callback table entry selected by render mode 8 points to the recovered
interior callback at `0x6f1d60` (table slot `0x8c8a20`). For each source XYZ
record, it writes XYZW to the destination: screen X from `x * 319.5 / z +
319.5`, screen Y from `239.5 - y * 319.5 / z`, scaled depth from
`(z - 1.0001) * 0.00004`, and reciprocal depth. When z is zero, the callback
uses the original 10000 reciprocal fallback. Values are stored as binary32;
source and destination strides are independent, and the callback updates both
global pointers after the batch.

`client/track_renderer_callbacks.py::transform_render_positions` translates
this mode-8 callback. 512 deterministic vertices matched all four outputs
bit-for-bit against direct execution of the installed callback across three
stride pairs; destination padding and final pointer positions matched as well.
This recovers the mode-8 callback path used by the track builders. The
mode-`0x10008` secondary depth/format callback and later material/draw behavior
remain to be translated.

The callback table reference and entry instruction are in REA Evidence
`ev_9f163d383d12674533c72615c2a05ac4146e3dcb3f60d2e6a50d02eff10b1052`; its
return boundary at `0x6f1de6` is recorded in
`ev_317b4270335a2d62bf7616b60de9b4f779b20c65baf8beb7503dca542e853975`.
