# Connected startup Num Lock, device input and cleanup

This batch composes the recovered startup controller and Num Lock wrapper/setter
with the existing device, keyboard-layout, window-policy and cleanup bindings.
The new probe is `startup_toggle_lifecycle`; older standalone and connected
probes remain available. It adds connected coverage, not new recovered entry
bodies or a playable-client claim.

## Original behavior and evidence

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA 6.7.0 / Ghidra 12.1.4, profile digest:
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.

- Wrapper `0x6bfc80`: Evidence
  `ev_a70577ea306a84a7816cca212dc0ecd56e0be483e85c2443045a769cb9c28f40`,
  complete inclusive body `0x6bfc80..0x6bfc8c`, 13 bytes.
- Setter `0x6bfc90`: Evidence
  `ev_977dcb5ee1987e1c0b7922a069c9b2c04ac325127df2277f68dbb1b36b84ce59`,
  complete inclusive body `0x6bfc90..0x6bfd10`, 129 bytes.

A compatible retained snapshot was loaded for the focused queries. Full records
and the exported snapshot remain private in
`evidence/startup-toggle-connected-rea.json` and
`evidence/startup-toggle-connected.snapshot.json`. No repeat installation-wide
decompilation was performed.

The setter allocates a local word using `PUSH ECX`, writes the scan byte into
that local, and finally consumes it with `POP ECX`. For the startup Num Lock
selector the scan byte is `0x45`. Therefore its outgoing ECX is the incoming
word with only the low byte replaced by `0x45`; API ECX clobbers do not survive
that final pop. This is an observed original x86 implementation effect, not a
portable Windows API guarantee or an ordinary authored return value.

The first connected comparison exposed this difference: the old device fixture
received its synthetic incoming word directly from a mocked preceding helper.
The real Num Lock body changes that word before device initialization. The new
binding projects that exact bounded transfer into the device initializer's
explicit `incoming_temporary` argument. It never manipulates host CPU registers.
The earlier mouse boundary still supplies the word's initial value; its real
body is not claimed by this particular probe.

## Connected verification

Sixteen persistent twelve-operation sequences exercise initial/repeated startup,
cleanup, explicit re-registration, key down/release and latch query. They vary
graphics/error behavior, device setup failure, full cleanup tables, initial Num
Lock state, returning API target changes, query/event register clobbers, and
incoming temporary words `0`, `0x71001400`, `0x800000ff`, `0xffffffff`.

Returning key APIs model state changes on key-up, with a profile that deliberately
keeps the state set to test repeated event pairs. Query-time event-import changes
and first-event import changes test that both events use the cached target.
Each step compares shared startup/device/queue/layout/registry/latch observations
and cumulative key API events, including device and policy state at those calls.
The original startup, wrapper, setter, device and cleanup instructions execute;
the native implementation never generates their expected outputs.

The complete checkpoint contains **103 implemented cells, 67,800 routine cases
and 112 connected traces**. Sixteen traces are new; reviewed-entry and required
function totals do not change. Fresh original-execution observations are replayed
by both MSVC and Zig. Python discovery passes 997 tests with seven skips.
Regeneration preserves every previous cell/probe content hash and all corpus
metadata, adding only the new probe shard and its index entry (about 247 KB).
Original binaries and full Evidence remain private.

Renderer, actual mouse initialization in this trace, remaining runtime helpers,
OS/DirectInput adapters, resources, networking and full client linkage remain
explicit boundaries. No host key events were sent and no original game process
was launched. This does not establish live startup or gameplay equivalence.

## Function ID queue review

The 77 initial Function ID hits are candidates, mostly in the existing CRT
region. Low-scoring file-lock helpers match both lock and unlock names; exception
destructors can match multiple classes and versions. Matching names across
Visual Studio versions do not identify the actual original compiler version.
No automatic library replacement, required-set reduction or inventory
disposition was made from these hits. The private candidate queue remains open
for function-level primary-evidence and compatibility review.
