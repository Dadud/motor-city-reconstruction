# Particle frame update core

The direct state-update slice of parent routine `0x527490` clears the frame's
52 type counters, ages group-zero trail records through `0x527360`, and then
visits the 600 particle records. Active records have their velocity/rate
fields scaled by the source lifetime factor and their remaining lifetime
decremented. A configured child emitter normalizes the parent's velocity when
nonzero, attempts its configured number of particles with unit scale, and
stops when the constructor returns no slot. When the frame animation bit is
set, spin/orbit adjusts X/Z velocity and advances the
per-record phase/rate/radius fields. The same frame gate applies color fade
when enabled by the source: it scales the per-channel limits by normalized
particle age, subtracts them with nearest-even x87 integer conversion from the
base color at `+0x4c`, and writes the result at `+0x48`. The x87 `FSINCOS`,
binary32 intermediate, and multiply-add store boundaries are preserved.
When the source-direction flag is set, the rate at `+0x34` is forced negative
for selectors above `+0.25`, positive below `-0.25`, and left unchanged inside
the strict dead zone.

On expiry, a nonzero respawn count with nonzero velocity normalizes that
velocity and attempts the requested number of child particles. Each attempt
uses a shared-RNG scale from `0.25` to `1.0`; successful spawns have their
lifetime halved and respawn count cleared. If the allocator reuses the expiring
slot, the constructor's staged velocity stores alias its acceleration input,
so the model preserves the native in-place read/write order.

1,024 direct parent calls compare the complete particle pool, 200 trail records,
all 52 counters, and six shared-RNG words exactly. The corpus covers both frame
animation-bit values, active/inactive and source-less records, varied source
lifetime factors, spin phase/rate/radius combinations, enabled and disabled
color fade with varied base colors and channel limits, direction selectors
around both dead-zone boundaries, expiry respawn counts, in-place slot reuse,
cadence suppression, and configured child emitters. It exercises 57,659 child
constructor attempts. All compared particle, trail, counter and RNG bytes
match exactly for the supplied valid source/configuration domain.

Static provenance: retained Ghidra pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
