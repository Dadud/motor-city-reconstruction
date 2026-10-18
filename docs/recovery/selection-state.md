# Six-word selection-state normalization

Original `0x4325c0` takes a writable six-word image in ECX and no stack
arguments. Its instructions read and write through ECX and end in a plain RET
at `0x43261f`. Several decompiled camera-handler callers print no argument;
the actual instructions at `0x4322d5` and `0x432531` load ECX with
`0x9aba98`. Follow-up producer and cycling evidence establishes four camera
presets, a selected camera index, and a preset slot. Earlier count/pending
labels were incomplete interpretations. The native context now carries all
six words and the [complete application controller](camera-selection.md)
composes this normalization. Actual callback handlers remain outstanding.

The fifth word is clamped to zero when signed-negative, then reduced modulo
five. The sixth is similarly clamped, then reduced modulo four. The first
four words use signed remainder modulo five without clamping. A zero first
remainder becomes one. EAX retains the signed quotient from division of the
fourth word, including when the first word is subsequently changed. Arithmetic
uses truncation toward zero; unsigned modulo would change negative inputs.

The hash-checked original body executes on 536 synthetic images: twelve repeated
edge values, twelve mixed edge rows, and 512 deterministic random images. Every
final byte and EAX is compared on MSVC and Zig/Clang. There are no callback or
child-body substitutions. The existing 59 cell observations and two separate
controller lifecycle traces are unchanged. At this helper checkpoint the aggregate had 60 cells and
6,865 complete-function cases; lifecycle traces remain separate.

The native self-test checks INT_MIN, INT_MAX, negative multiples, the forced
first remainder, and the negative fourth quotient together. Original pointer
faults are outside the host span contract. The actual handlers and their input
producers remain outstanding.

Validation: 138/138 MSVC and 140/140 Zig/Clang native tests pass; the Python
suite runs 985 tests successfully with seven skips. Layout audit remains at
98 registered offsets, 31 consumers, and zero shared unregistered offsets.
