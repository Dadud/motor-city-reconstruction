# Render rectangle field copy

`0x47f990` copies four 32-bit fields at offsets `+0x04`, `+0x08`, `+0x0c`
and `+0x10` from a source structure into the same offsets in the destination
object. The disassembly reads the `+0x0c` word before it writes `+0x10`, then
stores that saved word at `+0x0c`; this order is observable for overlapping
source and destination ranges.

`client/render_geometry.py::copy_render_rect_fields` translates the ordered
stores over a shared memory buffer. Five hundred twelve randomized original
calls match every byte, including overlapping ranges. The setter is shared by
the line/rectangle UI path and other game callers.

The retained Ghidra dossier is REA Evidence
`ev_ef3bddfc76ecaa24d720a93794085bb80dae04a5b6788a6c6a15904a832123bf`.
