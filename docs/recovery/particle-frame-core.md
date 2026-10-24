# Particle frame update core

The direct state-update slice of parent routine `0x527490` clears the frame's
52 type counters, ages group-zero trail records through `0x527360`, and then
visits the 600 particle records. In the supported path, active records without
child emitters, source-direction, color-fade or respawn effects have their
velocity/rate fields scaled by the source lifetime factor and their remaining
lifetime decremented. When the frame animation bit is set, the spin/orbit path
uses the per-record phase/rate/radius values to adjust X/Z velocity and advance
those fields. Its x87 `FSINCOS` and multiply-add store boundaries are preserved.

512 direct parent calls compare the complete particle pool, 200 trail records
and all 52 counters exactly. The tested inputs cover both values of the
frame's animation bit, active/inactive and source-less records, varied source
lifetime factors, spin phase/rate/radius combinations, and trail type counting.
All particle, trail and counter bytes match exactly. The parent's child-emitter,
source-direction, color-fade and respawn branches remain untranslated.

Static provenance: retained Ghidra pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
