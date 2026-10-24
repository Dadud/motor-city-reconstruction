# Particle record construction

Routine `0x527060` applies the emitter cadence and global mode gates, selects
the first inactive record or replaces the record with the lowest signed
remaining lifetime, then fills a 0x6c-byte particle slot. The translation
preserves the three supplied motion vectors, lifetime/size fields, randomized
velocity and color, source/configuration words, cadence byte, and the six-word
shared RNG transition. Extended x87 intermediates and binary32 stores are
modeled at the observed instruction boundaries.

512 direct calls compare the returned slot, all 600 records (including reused
slot bytes), and all six RNG words. Cases cover empty pools, inactive-slot
reuse, full-pool replacement, cadence/mode suppression, and deterministic
random emitter and motion inputs. Global time, effect mode, emitter data,
vectors and the initial RNG state are supplied. The parent particle simulation
and rendering remain outside this function-level translation.

Static provenance: retained Ghidra 12.1.4 pseudocode and direct x86
instruction inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
