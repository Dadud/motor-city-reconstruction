# Connected startup, mouse runtime and Num Lock

The new `StartupMouseBinding` replaces the startup controller's mouse-initializer
boundary with the recovered initializer and its connected runtime children.
It composes with `StartupToggleBinding`, so this probe also executes the real
Num Lock wrapper/setter. Keyboard initialization/layout and remaining startup
subsystems are still declared returning boundaries. The previous connected
keyboard/Num Lock probe remains intact; this batch does not claim a single
fully linked mouse-plus-keyboard platform implementation.

## Retained static evidence

Target: `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Provider: REA 6.7.0 / Ghidra 12.1.4, profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.

| Routine | Complete inclusive body | Bytes | Evidence |
| --- | --- | ---: | --- |
| Startup | `0x6bfa10..0x6bfc56` | 583 | `ev_efec5513eb8548562dc9f2b0ae2ae62669ecfc753bcbd49851053d8acc887943` |
| Mouse initialize | `0x6ef890..0x6efa5a` | 459 | `ev_166fbd665212c9f5878eae71fa53c8f2fda09d61223542775a15aa3d2bb64585` |
| Mouse state setter | `0x6efaf0..0x6efcad` | 446 | `ev_22ef938bbe58d31fcf48eb8ddfc827dd7dec8cff92c6c4082419d8189b9aa633` |
| Mouse driver setup | `0x6f06c0..0x6f0711` | 82 | `ev_56f5f64355be7be4e18a42f1ff5989f4b65643f0f36a21b27dd0a6c61aba4f27` |

Each listed body has one observed inclusive range. The retained startup dossier
explicitly identifies the mouse initializer as a direct callee. Full records
were read from private `evidence/rea-audit-6.7-startup-fresh.json` and
`evidence/rea-mouse-batch-final.bundle.json`; no new installation-wide analysis
or equivalent decompilation was needed. Geometry, callback and Num Lock evidence
is linked in [mouse geometry](mouse-geometry-progress.md),
[mouse callbacks](mouse-callbacks-progress.md) and
[connected Num Lock](startup-toggle-progress.md).

## Shared observations and connected behavior

Startup dimensions `0x8c4618/1c` are references used directly by the mouse lifetime
state. Diagnostics `0x8c4718`, `0xb2bba4/a8` alias the startup callback/file/line
words. Startup policy, mouse message registration and dispatch share the same
window/queue image. All mouse registration, reverse cleanup, shutdown and
re-registration use one cleanup registry. The bindings do not copy those globals.

The comparison shares the existing mouse runtime fixture and observation emitter
with the earlier standalone runtime runner. This keeps both runners on the same
declared API event format and checks the extraction against the retained corpus.

Thirty-two persistent 21-operation original-instruction sequences combine eight
mouse API profiles with four startup scenarios. They include graphics success
and returning errors, changes to dimensions after mouse setup, keyboard-boundary
queue mutations, factory/query/format/property failures, cooperative retry,
returning COM table/handle mutations, failed cursor conversion with fully defined
POINT words, signed wheel delivery, position/bounds changes, reporting/counters,
cleanup, repeated startup, explicit registration and repeated shutdown. A full
64-entry registry contains actual mouse shutdown callbacks, so its reverse run
executes recovered shutdown bodies rather than substituted callback returns.

Num Lock queries use fixed declared key-state observations. Import targets can
change at query/event boundaries while both events must retain their captured
target. These stubs intentionally do not emulate physical Windows key state.
The keyboard/device temporary-word contract is tested by the previous dedicated
probe; it is not observed across the mocked keyboard entry in this mouse probe.

After each operation, native replay compares the shared startup/mouse/window/
registry state, table selections, cumulative startup/key API logs and ordered
mouse API events. Synthetic factories write every output used by the mouse
initializer, including temporary and POINT words; unconstrained stack residue
is not a supported platform contract.

## Checkpoint and limits

The checkpoint retains **103 implemented cells and 67,800 routine cases**, with
**144 connected traces** (32 new). This is integration coverage of recovered
bodies, not new function completions or a whole-game completion percentage.
Fresh hash-checked original-instruction observations match both MSVC and Zig.
Python discovery passes 997 tests with seven skips. Regeneration preserves every
previous cell/probe content hash and all corpus metadata, adding one 87,653-byte
compressed probe record and its manifest entry. The previous probes and all
routine observations remain required by the aggregate runner and CI.

Windows/DirectInput, synchronization, cursor/context operations and other startup
subsystems remain synthetic bridges. Local context-object bytes, live resource
ownership, renderer/audio/networking and playable-client startup remain unresolved.
No game process was launched and no host key/cursor events were sent.
