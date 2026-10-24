# Particle frame update core

The direct state-update slice of parent routine `0x527490` clears the frame's
52 type counters, ages group-zero trail records through `0x527360`, and then
visits the 600 particle records. Active records without child emitters or
respawn effects have their velocity/rate fields scaled by
the source lifetime factor and their remaining lifetime decremented. When the
frame animation bit is set, spin/orbit adjusts X/Z velocity and advances the
per-record phase/rate/radius fields. The same frame gate applies color fade
when enabled by the source: it scales the per-channel limits by normalized
particle age, subtracts them with nearest-even x87 integer conversion from the
base color at `+0x4c`, and writes the result at `+0x48`. The x87 `FSINCOS`,
binary32 intermediate, and multiply-add store boundaries are preserved.
When the source-direction flag is set, the rate at `+0x34` is forced negative
for selectors above `+0.25`, positive below `-0.25`, and left unchanged inside
the strict dead zone.

1,024 direct parent calls compare the complete particle pool, 200 trail records
and all 52 counters exactly. The tested inputs cover both values of the
frame's animation bit, active/inactive and source-less records, varied source
lifetime factors, spin phase/rate/radius combinations, enabled and disabled
color fade with varied base colors and channel limits, direction flags with
selectors around both dead-zone boundaries, and trail type counting. All
particle, trail and counter bytes match exactly. The parent's child-emitter
and respawn branches remain untranslated.

Static provenance: retained Ghidra pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
