# Recovery and acceptance ledger

This ledger separates recovered building blocks from a complete game. It is an
implementation checklist, not a claim that the original client has been restored.
The Python runtime remains a development harness. A native port must retain these
distinctions rather than presenting prototype behavior as original behavior.

## Evidence and status rules

- **Recovered** means the stated bounded behavior has original executable or asset
  evidence and a repeatable comparison. It does not imply its entire subsystem works.
- **Partial** means some original behavior is implemented but required branches,
  integration, or runtime acceptance remain missing.
- **Prototype** means authored behavior used to exercise the application, without a
  claim that its rules match the original.
- **Unknown** means no verified implementation of the required behavior exists.

Every change to a status must link a source identity, research note, repeatable
verification command or fixture, and observed result. Preserve unknown units and
fields explicitly. Never substitute passing synthetic tests for live acceptance.
Record the executable SHA-256, operating system, dependency/build versions, input
scenario, comparison tolerance, and any substituted calls in verification records.
Raw executable bytes, pseudocode, private account data and runtime captures remain
outside the published repository.

## Feature map

The [cell comparison checkpoint](recovery/cell-comparisons.md) connects all
67 implemented cells to a shared original/native corpus: 17,589 synthetic cases
match bit-exact, including whole image writes and two restored null-pointer
branches. Empty comparisons now fail. W0 coverage is now 63 of 658 required entries, plus three supporting dependencies in W6 and one release producer in W5. The [entity and mask batch](recovery/entity-table.md)
also shares packed layout contracts with existing flag readers.
The [camera application controller](recovery/camera-selection.md) now composes
preset normalization and mode/context selection, with actual handlers still
substituted and twelve separate connected traces. The subsequent
[cycling controller and explicit mode child](recovery/camera-cycling.md)
add preset/subject cycling and eight more connected traces.
The [input state batch](recovery/input-key-state.md) recovers raw-key/latch
queries and the real release-message producer; six connected traces use no
input-body substitutions. Key-down queuing and live message dispatch remain open.
The [record stack batch](recovery/record-stack.md) preserves unsigned cursor
comparisons and staged-copy ordering, including tested overlapping byte views.
The [record controller batch](recovery/record-transitions.md) connects initialization,
retention, push/replace, activation and stack lookup in two original/native traces.
Callback-entry images and mutations are compared under explicit handler
substitutions; actual handler bodies and owner integration remain unfinished.
The MSVC `__int128` blocker is resolved
with portable integer arithmetic, checked against 5,464 Python cases on MSVC
and Zig/Clang. Both compilers reproduce 135 Python startup records exactly;
the original-code oracle still needs its documented one-ULP angular tolerance
in 17 of those cases. See [startup record](calculations/startup-record.md).

The latest source translation adds [complete base body construction and catalogue
sample customization](calculations/body-construction.md), native owner-binding
producers, and a connected startup-body phase matching 320 original scenarios.
The main owner initializer and upstream model assembly remain partial; this does
not close the original driving acceptance gate.
The projected-area query `0x483450`'s final 321x241 occupancy count/bounds helper
`0x483f60` is now translated in Python and C++ and matches seven direct masks
against the installed executable. Mesh traversal, projection rasterization and
the full projected-area result remain unimplemented. Its scanline numeric leaves
`0x483f00`/`0x483f30` (float ceiling/floor conversions) also match 256 direct
original inputs each in Python and C++; the triangle-edge and pixel-fill stages
remain unimplemented.
The main initializer's [load, balance and brake producers](calculations/startup-balance.md)
are now also translated in Python/C++; their complete original calls match on
authored configurations and all eight supported stock configurations.
Its [135-entry resistance table and surface helper](calculations/startup-resistance.md)
also match complete original calls; the projected-area producer and integrated
shift-curve publication remain unresolved.
The downstream [four-wheel owner setup](calculations/owner-wheel-setup.md)
`0x53b8a0` and stance-adjustment child `0x53b3c0` match 56 varied complete
synthetic owner images and 16 supported assembled stock configurations
byte-for-byte. They consume finalized configuration and prior owner geometry;
upstream owner startup and live geometry/resource acquisition remain open.
The prepared-model bounds/centering entry `0x52be40` now consumes recovered
stock body flags and collector records for eight installed vehicles; complete
FCE bytes and output extents match the original exactly. This extends stock-body
surface selection coverage without closing component loading or owner-list
construction.
`client.owner_startup.initialize_owner_startup` composes recovered body setup,
record publication and final wheel initialization with explicit model/scene
inputs. Tests cover this stage handoff; the original resource-selection wrapper
and full `0x43a990` execution remain untranslated.
The [startup force helper and 112-sample acceleration tables](calculations/acceleration-table.md)
match 720 helper calls and 36 complete producer calls (8,064 stored samples)
bit-exactly with real original torque-lookup children and surrounding-sentinel
checks; MSVC native/Python comparisons match the same corpus exactly.
Cross-reference and instruction-level evidence now identify the producer's
sole caller: the owner-binding initializer `0x53a1f0` builds the record at
`EBP-0x4d8` per gear from recovered gear-force tables minus recovered startup
resistance, derives the shift thresholds from the adjusted curves' crossing
sample counts (gears zero/one pinned to `-10000`, top gear to `12000`, producer
index biased +2 gears), and stores the finished 0x4a8-byte record at owner
`+0x17ec`; record `0x104` is the rear tire radius used as the startup-force
denominator. The [full constructor](calculations/startup-record.md) is now
translated and ported: seven oracle cases (4/8/6/5-gear, marker-present,
marker-missing and NULL-model inputs, four supplied scene-area returns)
compare the whole record bit-exactly and confirm the missing-marker failure
returns 0 with an unmutated owner; the native port matches the translation
bit-for-bit over the same corpus. The `FUN_00483450` scene-area query itself
has a bounded decoded-geometry translation and synthetic original comparisons;
the live registry/allocator integration is still supplied as an explicit input.

| Feature | Current status and evidence | Remaining recovery path | Acceptance scenario |
| --- | --- | --- | --- |
| Startup and asset discovery | Partial: explicit read-only asset root, bounded VIV reads and case-insensitive lookup; `assets.py`, `tools/viv.py` | Recover required startup resources and original loading/failure sequence; migrate platform startup | Start from a fresh installation on Windows and Linux; missing/corrupt required assets produce an actionable error without modifying originals |
| Vehicle geometry and textures | Partial: [native FCE/FSH garage](native-garage.md); 315 original archives/99,608 positions and 254 texture image checksums match Python, original textured renders pass on Windows | Unsupported codecs, authentic materials/paint, attachment visibility, stock assembly and animation | Decode installed vehicle corpus; compare representative assembled cars to original views and reject malformed content safely |
| Tracks and world presentation | Partial: base track meshes, spatial lookup and support; `track*.py`, `world.py` | Objects, effects, material/render ordering, visibility and full track variants | Traverse every supported track with original assets; compare landmarks, surfaces and object placement |
| Catalogue and stock assembly | Partial: typed catalogue, physics fields and component interpretation; `catalogue.py`, `assembly.py`, `physics_data.py` | Resolve unsupported assemblies, conversion cases, dimensions and nested placement | Assemble stock corpus with explicit reports for every rejected record; compare complete geometry and component inputs |
| Owned and modified vehicles | Partial: enrichment/discovery and verified insertion, pruning, ordering, linking and numeric totals connected in the [postload sequence](owned-postload.md); [outer descriptions](calculations/owned-component-descriptions.md) retain explicit leaf/localization inputs | Recover part-specific descriptions and localized labels, complete DB loading/handoff, mechanical aggregates and online refresh; verify integration on actual owned cars | Load an actually modified owned car without stock substitution; compare complete hierarchy, attachments and derived values |
| Engine calculations | Partial: standalone unboosted nineteen-knot core matches 46 complete original records; integration matches 44,635 original steps; ordinary final curves match eight stock engines and 35 isolated branch cases; [finalization](calculations/engine-curve-finalization.md), [engine](calculations/engine-dyno.md), [cycle](calculations/cylinder-cycle.md) | Boost, special carburetor mode, native finalizer port, native abort semantics and wider domain coverage | Compare full engine curves and intermediate state for supported stock and modified engines, including boundary modes |
| Motion and support geometry | Recovered bounded calculations: pose updates and contact geometry; [motion](calculations/vehicle-motion.md) | Confirm full call ordering, units, wheel sizing and stance in the integrated simulation | Original versus reconstruction pose/contact traces agree under documented tolerances and identical inputs |
| Tire/suspension/drivetrain/brake forces | Partial: recovered tire dimensions, spring/shock validation, [combined steering/tire update](calculations/tire-update.md), [wheel curve consumers](calculations/tire-response-curves.md), [resistance contribution](calculations/rolling-resistance.md) and stock input bridge; full integrated force model unknown | Follow [driving recovery map](driving-recovery-map.md): input and curve producers, integrated load sequence, gears/clutch, differential, brakes, surfaces and aero | Match original acceleration, gear changes, braking, skid and cornering scenarios for multiple configurations |
| Collisions | Partial: [response, impulse-to-motion and plane-height helpers](calculations/collision-helpers.md) match original execution; [game task registration](../client/game_schedule.py) is ported; [dispatcher, terrain query and object-pair call order](collision-world.md) traced statically | Recover broad/narrow phase, contact/impulse creation, damage, recovery and update order; port and compare enclosing routines | Compare track-object and vehicle collisions, resting contacts and post-impact behavior |
| Offline driving | Prototype: authored 120 Hz terrain-following bicycle model; `driving.py` | Replace forces only after original calculations are verified; retain harness for comparison | Recovered model passes repeated original driving scenarios with reproducible outcomes |
| Race rules and results | Prototype: inferred course closure and ordered gates; `racing.py` | Recover actual event definitions, start/finish rules, penalties, standings and result consumers | Original-equivalent starts, checkpoints, finish classification and timing across event types |
| Garage and customization UI | Partial garage preview and body/component presentation | Recover menus, part installation/removal, paint/material changes, validation and state transitions | Complete garage editing flow renders and persists the selected configuration correctly |
| Shops, repairs and economy | Partial recovered part valuation; [valuation](calculations/owned-part-valuation.md) | Recover transaction builders, replies, inventory changes, limits and rejection handling | Purchase, install and repair scenarios match original values and server-confirmed state; rejected requests leave state consistent |
| Progression | Unknown complete flow | Recover profile/event/progression consumers and authoritative updates | Race rewards and unlocks survive restart and agree with server/original account state |
| Account and personas | Partial: blocking orchestration plus private [account check](online-account.md) and [fan-server flow check](fan-server-testing.md) through login, persona list, lobby, primary MCOTS and optional garage startup; [startup key value](nps-key-initialization.md) matches nine bounded original cases; live acceptance unverified | Asynchronous lifecycle, playable UI, reconnect and documented live MotorCity Revival runs | Authorized account logs in, selects persona, connects lobby and primary, loads garage counts on both platforms; denial/cancellation expose no secrets |
| Lobby and chat | Partial: transport/login/channel/send recovery plus room validation; [channel codec](lobby-channel-codec.md) reproduces `0x106` payloads and `0x214`/`0x215` reply fields in bounded native comparisons (27 payloads, nine capacity rejections, six reply cases); live room join and race channel not implemented | Recover authenticated room argument construction, channel lifecycle, game-network task dispatch integration, presence/chat UI and reconnect behavior | Join actual lobby, add a room channel, exchange supported messages and reconnect with consistent presence |
| Primary game data | Partial: encrypted/compressed session, paged fetching and persona startup sequence (0xac/0x6c/0x108) exercised by fan-server check; [session](mcots-session.md), [data](post-login-data.md) | Additional service joins, complete owned-car assembly, background dispatch and unsolicited 0x198 handling in a playable client | Load live owned modified car data with optional catalogue enrichment; process unsolicited updates without losing synchronization |
| Online race and synchronization | Partial: static channel/task evidence and bounded channel-record recovery; [race-entry research](race-entry-research.md) reports missing task order and authenticated arguments; patch update-rate settings are configuration observations; live room join and position sync not implemented | Recover authenticated room negotiation, original task scheduling, game-start dispatch, peer sync, corrections, disconnects and finish reporting | Join and finish a supported fan-server race with correct remote motion and persisted results |
| Audio | Unknown complete implementation | Inventory sound formats and recover sound selection, engine/load transitions, mix and lifecycle | Original-equivalent engine, tire, impact, interface and music behavior on both platforms |
| Settings and input | Partial keyboard/display preferences; `settings.py`, `app.py` | Controller mappings, configurable controls, audio/display persistence and focus handling | Keyboard/controller driving, focus loss and settings persistence work on both platforms |
| Native runtime | Partial calculation ports, bounded Lua and [original-geometry garage](native-garage.md); native driving/online unknown | Follow [native migration](native-migration.md), preserving comparison fixtures | Reproducible Windows/Linux packages run real original-asset gameplay without Python, REA or Ghidra |
| Mod kit | Partial [working data alpha](mod-kit-tutorial.md): six resource kinds, manifests, dependencies, explicit overlays and four tools; [Lua alpha](mod-lua-alpha.md) supports directory/ZIP packages, reproducible archives and real bounded native registration/inspection through `tools.modkit script` | Native game resource loading, supported gameplay events/state, script dependencies/replacements and complete compatibility documentation | Outside developer creates, validates, packages and runs a content/script mod using published instructions |

## Ordered gates

Current work follows the [approved source recovery plan](recovery/plan.md).
The [installation export catalogue](recovery/export-status.md) distinguishes raw
decompilation from translation. [Wheel initialization](calculations/owner-wheel-setup.md)
and [part bounds](calculations/model-bounds.md) now have complete bounded original
comparisons; assembled model geometry and full owner initialization remain open.

Thirty-two [mechanical component loaders](calculations/mechanical-component-loading.md)
now recover engine-block, head, camshaft, crankshaft, rods, pistons, valve-train,
transmission, rear-end, rim, spring, shock, brake and tire validation, writes and
quality, plus intake/exhaust/auxiliary engine, body/accessory and axle-bar loaders.
Their complete bodies match 8,031 original cases, including forty-seven actual
stock Ford components (the standalone corpus also tests unused duplicate parts).
Another thirty-eight-call partial stock sequence matches all original images.
Native ports match 7,984
authored cases; the mechanical numeric copy and paired expansion have separate
bounded comparisons. The stock inspector expands 45 catalogue entries to 57
components and reports unsupported handling explicitly. Tire auxiliary packing
matches six original runs including eighteen actual database rows, with substituted
typed DB/allocator services. The [ordinary unboosted engine finalizer](calculations/engine-curve-finalization.md)
matches eight complete stock configurations and 35 isolated branch cases in Python.
The [complete supported mechanical assembly](calculations/mechanical-assembly.md)
now matches eight stock configurations and eleven missing-part/rejection/duplicate
scenarios against whole original calls, without substituted callees. It includes
dispatch, quality, total mass, weight and final engine curves. The stock driving
report carries finalized mass, axle levers and gear tables. Other component
families, special engine modes, native assembly/engine-curve port, geometry and
owner startup still block driving.

The [assembly numeric finalizer](calculations/assembly-finalization.md) now
recalculates component-based weight distribution and the original postload
fallbacks, overrides and weighted accumulator. The complete weight helper and
the enclosing numeric tail each match 728 original executions exactly; native
ports retain corresponding differential runners. This supplies another startup
producer, but does not complete component loading, total mass accumulation,
quality updates or full startup. The stock driving gate remains open.

The [connected drivetrain](calculations/drivetrain-stages.md) now executes all
eight engine driving children with brakes, loads, environment and tires in the
Python research harness. The five newly recovered numeric bodies pass 3,360
whole-owner/configuration comparisons. Two integrated corpora pass 576 original
controller ticks, including 480 engine/brake ticks and 960 drivetrain service or
effect observations. Rolling resistance and wheel projection rounding fixes also
land in C++. The five new drivetrain bodies now have a native port matching
3,377 Python cases exactly. The [gear-table producer](calculations/gear-binding.md)
matches 225 original executions and its native port exactly, and supplies the
shared tables in another 576 integrated controller ticks. Complete native
shared-state driving orchestration remains required.
Stock initialization, terrain projection, remaining preparation, gear services,
actual component implementations, collisions and driven runtime captures remain
open. The following earlier results describe narrower stages of this work.

The larger [driving pipeline](driving-pipeline.md) now compares 288 original
controller ticks with actual support prediction, input smoothing, load producers,
body environment and tire-force stages. Terrain selection/projection, remaining
preparation, engine/brake integration and actual component delivery remain supplied.
The [separate engine pipeline](calculations/engine-pipeline.md) passes 514 original
scenarios and 1,696 retained ticks with zero error and has a native port. The
[owner-binding producers](calculations/owner-binding.md) pass 154 original numeric
cases; finalized configuration/model inputs are still explicit observations.
These results expand integration coverage without completing faithful driving.

The [controller force pipeline](driving-pipeline.md) now checks 288 complete
original controller calls with six actual force stages and linear integration.
Its typed support adapter consumes the separately verified
[predictor](calculations/support-prediction.md). The
[complete torque consumer](calculations/engine-torque-update.md) matches 1,094
original cases, with producer/effect boundaries explicitly supplied. The
[stock startup audit](calculations/stock-driving-startup.md) identifies actual
vehicle 101/Drag data and missing assembled inputs. None of these closes the
offline driving gate: authentic initialization, terrain service, remaining child
integration, event interleaving and driven original-client comparisons remain.

The connected support variant executes another 288 original controller ticks,
including low-support branches, with 1,152 exact terrain-query handoffs. Terrain
projection remains supplied. The [body configuration initializer](calculations/body-configuration.md)
matches all configuration bytes across 146 records, including actual vehicle 101.
Those outputs now appear in the stock inspector; final assembled mass/inertia
and semantic validation remain open.

[Wheel-spin integration](calculations/wheel-spin.md) now matches 2,592 original
numeric cases and [combined-slip force limiting](calculations/combined-slip.md)
matches 1,296. Their C++ ports match the Python corpora exactly. The expanded
[shared-state force sequence](driving-force-sequence.md) checks six connected
stages with 1,152 comparisons across repeated calls. Component delivery is
supplied with exact argument checks; actual component effects, authentic input
production, complete child-stage integration and scheduler clock/runtime behavior
remain required.

The [driving recovery map](driving-recovery-map.md) now records scheduler lists,
conditional force-call order and comparison targets for each driving subsystem.
The [two wheel response consumers](calculations/tire-response-curves.md) match
1,728 complete original-function cases with synthetic tables. Table production,
slip/normal-load sources and integration into original driving remain required.
The [wheel resistance contribution](calculations/rolling-resistance.md) matches
1,344 complete original-function cases with its mode predicate substituted.
Its component/input producers and integration with traction/braking remain partial.
The [acceleration-driven load correction](calculations/load-transfer.md) matches
1,250 complete original-function cases without substituted calls. Initial loads,
following suspension corrections and enclosing driving integration remain partial.
The [initial support-mask loads](calculations/normal-load.md),
[wheel-speed projection](calculations/wheel-speed-projection.md) and
[following suspension correction](calculations/suspension-load-correction.md)
now match 2,016, 1,296 and 1,730 complete original-function cases respectively.
Their C++ ports match the Python corpora. A [shared owner-image sequence](wheel-load-sequence.md)
matches 1,728 scenarios across three load stages, excluding intervening helpers
and surrounding integration. The controller and scheduler driving branch now
have separate comparisons below. Real support/input production and complete
tire/drivetrain integration remain required.
The [speed-dependent steering response](calculations/steering-response.md) now
matches 2,064 complete original-function cases and its C++ port matches the
Python corpus. The [combined steering/tire update](calculations/tire-update.md)
now matches 3,948 complete original-function cases with zero observed absolute
error; its C++ port matches that Python corpus exactly. Original steering,
trigonometry, both curves and the per-wheel predicate execute in the oracle;
only virtual interface operation 5 is supplied. The
[predicate](calculations/vehicle-gate.md) separately passes 50 original comparisons.
Controller input, maximum steering, curve/secondary-angle/surface producers,
predicate scheduling and integrated driving remain required. All 39 local
native checks pass; Python runs 639 tests, with 632 passing and seven skipped.
These are local Windows results; Linux checks are configured in CI, not claimed
as a completed gameplay acceptance run.

Parallel driving recovery adds the following bounded increments. None completes
the enclosing drivetrain, brake, body integrator or collision tick:

| Recovered scope | Original comparisons | Remaining enclosing behavior |
| --- | --- | --- |
| [Driving RPM and torque coupling](calculations/driving-engine-rpm.md) | 2,592 complete RPM cases and 868 coupling-tail cases, exact | Earlier torque/boost/health calculation, gears and engagement producers |
| [Engine dispatcher and curve lookup](calculations/engine-update.md) | 1,159 complete dispatcher cases, exact, with actual RPM/lookup and 12 supplied child-write scenarios | Other engine child bodies and interface observations, authentic inputs and integrated engine/drivetrain execution |
| [Engine condition and thermal links](calculations/drivetrain-links.md) | 1,136 complete original cases, exact; damage/effect consumers supplied with mutation checks | Actual effect consumers, component units/input assembly and engine dispatcher integration |
| [Control smoothing and dispatch](calculations/control-update.md) | 844 complete original cases, exact, including full owner snapshots at child boundaries | Remote input, complete gear state machines, external queries and actual controls-to-driving integration |
| [Wheel-force/spin correction](calculations/wheel-force-correction.md) | 2,880 complete cases, exact | Authentic brake-force and coefficient producers; integrated driving |
| [Brake initialization and thermal prefix](calculations/brake-thermal.md) | 432 cases, exact; world query supplied | Authentic component inputs; enclosing numeric forces now recovered separately below |
| [Complete numeric brake update](calculations/brake-forces.md) | 376 complete cases; maximum error `0.0001220703125`; actual fade/quality/world/controller helpers | Component wear-event consumer, authentic input producers and integrated braking traces |
| [Wheel-spin integration](calculations/wheel-spin.md) | 2,592 complete numeric cases; maximum error `1.52587890625e-5`; exact event arguments | Component effects, authentic component/input producers and caller scheduling |
| [Combined-slip limiting](calculations/combined-slip.md) | 1,296 complete numeric cases; maximum error `0.00048828125`; exact ordered effect arguments | Authentic force/contact inputs, component effects and integrated skid traces |
| [Vehicle controller and connected linear update](calculations/vehicle-update.md) | 2,607 controller cases; exact compared outputs and ordered calls with owner byte checks | Other child-stage bodies/observations, authentic inputs, assembled-car integration and full collision tick |
| [Scheduler](scheduler.md) | 648 insertion, 365 executor, 1,440 selector/interleaving and 81 catch-up comparisons | Wall-clock timing, mode/input producers, full outer state machine and actual callback integration |
| [Body moments and force orientation](calculations/body-moments.md) | 1,440 complete moment cases, maximum error `1.1920928955078125e-7`; 243 orientation cases exact | Aero, body transforms, authentic input producers and complete velocity integration |
| [Axle vertical-load adjustment](calculations/body-vertical-load.md) | 486 complete cases, exact, including original helper | Authentic body/component inputs and connected load sequence |
| [Body resistance and connected environment](calculations/wind-drafting.md) | 432 arithmetic-stage cases, 432 connected density/weather cases, and 432 full density/wind/drafting/body cases, exact; only virtual mode supplied in full chain | Authentic environment/component inputs and complete vehicle force integration |
| [Wind and drafting](calculations/wind-drafting.md) | 5,760 wind and 865 drafting complete original cases, exact, including ordered selection and cross-car writes | Track/counter/mode and authentic vehicle geometry producers, complete vehicle force integration |
| [Air density](calculations/air-density.md) | 260 complete original cases, exact, including weather/floor helpers | Authentic altitude/environment producers and track settings |
| [Vehicle preparation and support disturbance](calculations/vehicle-preparation.md) | 251 preparation and 384 support cases, exact, with original numeric helpers and a retained-precision regression | Authentic transforms/support fields and surface lookup/table producers; connected driving |
| [Collision helpers](calculations/collision-helpers.md) | 1,731 response, 1,920 impulse and 48 height cases, exact | Contact detection/creation, impulse selection, persistent contacts, damage, recovery and full tick |

All new native ports match their Python corpora exactly. Local Windows checks:
61 native tests pass; 766 Python tests run, with 759 passing and seven skipped.
`python -m tools.native_driving_compare build/native-check` runs these new
differential corpora together; Windows/Linux CI includes the same command.
The [shared-state force sequence](driving-force-sequence.md) adds 96 twice-repeated
scenarios and 1,152 stage comparisons, with maximum error
`0.000244140625`. It validates six-stage output handoff while explicitly
excluding the original caller, intervening branches and scheduler.

Further networking recovery: [channel argument initialization](lobby-channel-record.md)
matches 36 original constructor and 36 record-copy cases, preserving allocation
holes. [Native plain NPS framing](native-nps-framing.md) passes 108 serialization,
21 stream-decode, 12 header-decode and 66 rejection comparisons against Python.
All 18 native and 513 Python checks pass locally on Windows. The
[race-entry audit](race-entry-research.md) removes unsupported task ordering and
transport selection; authenticated room arguments and live races remain missing.

Latest bounded networking increment: [C++ channel codec](lobby-channel-codec.md)
matches 136 portable payloads and 11 rejections on Windows, with 17 native tests
passing. The [fan-server tester](fan-server-testing.md) now records safe failure
stages and exports private-data-free reports. Installed Revival shard 44 passes
preflight; authenticated lobby/garage acceptance and live racing remain unverified.

1. **Recovery map:** every required feature above has an owner/research path,
   concrete scenario and source evidence inventory. An unknown remains visible.
2. **Complete vehicle:** stock and owned modified assemblies include the original
   finalization/linking passes and fully derived simulation inputs.
3. **Faithful offline driving:** full engine and force integration replace prototype
   handling; original event rules replace inferred time trials.
4. **Complete offline flow:** garage, customization, menus, audio and results work
   with actual assets on both operating systems.
5. **Verified online flow:** account → persona → owned garage → lobby → race →
   finish → persistent result → reconnect succeeds against the configured server.
6. **Developer release:** reproducible native packages and a documented mod kit
   pass an independent build-and-mod exercise.

## Verification record requirements

The [native channel-record port](native-lobby-channel-record.md) now belongs to
the CMake build: 192 constructor and 224 record images match the original-verified
Python implementation, with six invalid runner sizes rejected. All 19 local
Windows native checks pass. The [channel reply codec](lobby-channel-codec.md)
includes opaque `0x213` status decoding and a bounded single-pending-reply model;
live orchestration and authenticated room arguments remain incomplete.
The [original reply oracle](lobby-channel-reply-evidence.md) matches eight
status reads, eight return conversions and 48 mailbox scenarios, with the
serializer boundary explicitly substituted. These are bounded recovery checks,
not authenticated joins.

The [channel reply wait](lobby-channel-wait.md) now matches 25 bounded original
scenarios and 428 Python/native scenarios, including timeout/cancel/disconnect
precedence and cleanup. Its sleep-unit conversion matches 12 original arithmetic
cases. All 532 Python tests and 20 local Windows native checks pass. Authenticated
room producers, transport/listener integration and live joins remain separate
required work; these results do not complete online acceptance.

The [room-request producer](room-request-production.md) now reproduces the
observed native argument from explicit room state: 80 original argument cases,
three guard paths and four callback-return cases match. Its C++ port matches
60 argument cases and five boundary rejections. The
[composed channel pipeline](room-channel-pipeline.md) matches another 30 original
constructor/record/payload paths under explicit synthetic allocation and binding
inputs. [Local worker records](async-worker-record.md) now identify the previously
opaque header as operation ID and worker result, with 42 bounded original
comparisons. None of these supply authenticated room selection, worker queue
ownership or a complete live race-entry flow.
The [room result transition](room-join-result.md) matches 72 original full-image
cases and has a native port, including successful notification arguments and
negative-result state preservation. These bounded modules are now built into
`mco_core`; connecting them to authenticated state and the listener remains
required.

The [completion queue](async-worker-completion.md) now reconstructs destructive
first-ID-match retrieval, including null-output removal and signed-result
decoding, in Python and C++. Its bounded original runner matches 252 queries
and six zero-ID exception boundaries. Real worker scheduling, locks and live
room delivery remain outside these comparisons.

The [server-selector binding](room-server-binding.md) now identifies the embedded
room's selector as the successful local connection-interface return. Eighty
bounded original dispatcher cases match full-image writes and helper call order.
The configured shard ID is not substituted for this connection result.
Authentication, connection-handle ownership and live room selection still need
integration and verification.

The [settings assignment](room-settings-transfer.md) selectively copies the
actual room fields, preserving string tails and unrelated state. Eighty original
whole-image transfers match without substituted calls, and 80 C++/Python cases
match. The [connection registry](connection-registry.md) now recovers the local
counter (including valid initial zero and wrap) and existing-connection identity
lookup, with 64 original counter-range cases and 144 complete original lookups.
Native server binding also matches 80 C++/Python cases. These modules establish
upstream sources; authentication, insertion/lifetime, listener scheduling and
live race entry remain required.

[Room disconnect preparation](room-disconnect.md) now resets the original settings
fields and retains old IDs in initialized task arguments. Thirty-two disconnected
returns and 64 connected preparations match the original; its C++ port matches
96 Python cases. The [disconnect action controller](room-disconnect-flow.md)
now reproduces pending waits, completion queries and application-pump decisions
in 308 complete original-function scenarios; its native port matches 69 Python
action traces. The [channel-close codec](lobby-channel-close.md) recovers the
opcode `0x105` frame with 32 original close paths, five raw serializer cases,
eight lower-helper logoff paths and 40 missing-registry paths; 81 native/Python
encodings match. These remain isolated models, not live tester orchestration.
Actual worker scheduling, container effects and unspecified task padding remain
excluded. The [server disconnect follow-up](connection-disconnect.md)
maps registry removal/reference release and matches 24 original result paths and
216 communication destructor ownership guards with explicit substitutions.
Actual socket closure, asynchronous cleanup, complete registry mutation and live
reconnect still require implementation and verification.

[Room settings selection](room-selection.md) now matches 144 complete original
paths and 24 initializer cases; the C++ port matches 72 Python selections and
24 initializers. [Race-room selection](race-room-selection.md) identifies actual
metadata/global sources and matches 210 bounded caller cases, including 48
unsigned decimal room-name overrides. [Selected-event connection](race-join-transitions.md)
distinguishes secondary-server LOBBY entry from race-room start, with 28 original
callback comparisons. Metadata construction, actual room-list/cache population,
game task execution and live race entry remain incomplete.

The first private live authorization test exposed Revival's compact hash-pair
response. The [decoder correction](revival-authorization-envelope.md) now reports
an explicit authorization denial instead of a protocol/data failure. Binary
login, personas, lobby and garage were not reached; successful live acceptance
remains unproved, and server version remains unreported.

The [game-start completion and room polling controller](game-start-flow.md) now
matches 208 bounded original-function scenarios and 63 C++/Python action traces.
The start-request wire layout, live worker/cache driver and session integration
remain unresolved; this does not complete race entry.

Current batch verification on Windows: 950 Python tests (943 pass, seven skipped)
and 75 native checks pass, plus the separately recorded original comparisons above. Linux and live
fan-server race acceptance remain unverified.

The [engine-to-controller bridge](driving-pipeline.md#engine-bound-into-the-vehicle-tick)
now compares 288 retained original vehicle ticks with real controls, loads,
environment, engine torque/RPM/condition and tire forces connected. With actual
support prediction, 192 supported ticks execute the engine and 96 low-support
ticks skip it. Terrain projection, remaining preparation, engine setup/control,
engagement/clutch, wheel-drive distribution, finalization and brakes remain
supplied. Original stock-car startup and faithful driving acceptance remain open.

The [brake-to-controller bridge](driving-pipeline.md#brakes-bound-into-the-vehicle-tick)
extends that comparison with original brake thermal/force bodies and selected-gear
inertia lookup. The support-prediction corpus checks 192 brake ticks and 1,152
interleaved wear/controller observations; authored contacts check 288 brake
ticks and 1,728 observations. Longitudinal forces and spin adjustments are checked
before tire/spin consumers. The documented derived wear-observation difference
remains visible, with exact checks against each trajectory's own source fields;
physical tolerances are unchanged. Authentic brake initialization, inside-loop
component effects and integrated original-client braking remain unproved.

The dependency-linking pass is now implemented in isolation and documented in
[owned component dependencies](owned-component-dependencies.md). Its 64 bounded
original-CPU cases include the actual type-cache helper. Root selection and
parent/family linking are now recovered separately, with 96 original-code cases
per pass and matching C++/Python outputs. [Type-cache resolution](part-type-cache.md)
matches another 64 original-code cases. Preceding finalization and integration of
these passes remain required before complete owned-car startup.

The [induction pruning phase](owned-induction-pruning.md) of finalization matches
97 original-code cases and has a native port. Earlier missing-part insertion and
the full finalizer's entry conditions remain unresolved; pruning is not a complete
replacement for that finalizer.

Numerical checks include branch/boundary inputs, update order, rounding and explicit
tolerances; bit equality is required where recovered serialized layouts demand it.
Whole-runtime traces include controls, initial vehicle/track state and elapsed time.
Test stock and modified engines, surfaces, contacts, collisions and race types.
Test truncated resources, invalid indexes, cyclic trees, resource limits, casing,
invalid mods, cancelled sessions, disconnects and rejected transactions.

Network records name the tested server configuration/version when observable,
scenario, packet direction/operation and result without credentials or account
payloads. Synthetic sockets demonstrate transport behavior, not fan-server approval.
Linux generated-geometry rendering demonstrates a graphics path, not original-asset
driving or audio. An isolated native function comparison demonstrates only its
stated instruction range and supplied preconditions.

Completion requires all required rows to lose their prototype/unknown gaps and
pass their acceptance scenarios. Record remaining mismatches rather than adjusting
reference outputs to fit the reconstruction.

## Source translation: world-object motion callback

The scheduled callback at `0x5779d0` now has a typed Python translation and a
native C++ translation. The original mutates linear velocity at owner offsets
`+0x14/+0x18/+0x1c` and angular velocity at `+0x38/+0x3c/+0x40`. A nonzero signed
short at `+0x3bc` multiplies all three angular-velocity components by `0.9`;
otherwise linear-velocity components strictly below `0.5` in magnitude are
zeroed. Each of the three angular-velocity checks strictly below `0.05` writes
zero to the middle component, matching the actual binary even when the check
reads one of the other components. No claim is made about
the surrounding object layout or other callbacks.

Evidence `ev_e9405a05e3888c4f9d1d107eefc302d11a9cc9dd6dd8abf9509a3e42fcd6a6f1`
records the decompilation. `tools/verify_world_object_damping.py` compares five
branch and threshold cases against the exact SHA-verified installed executable.
The focused Python tests pass, and the native suite passes 194/194 tests. This is
one recovered game callback, not a complete world simulation.

## Source translation: world-object maintenance pass

The primary schedule's `0x4265f0` pass is also translated for its observed
active-object logic. For each active record it calls `0x520c20`, computes the
angular-velocity magnitude, damps linear and angular velocity when owner `+0x350`
is below owner `+0xd8`, caps angular-velocity magnitude at 10, and adds `0.01` to
the first angular-velocity component when the unsigned counter at `+0x3bc`
exceeds 32 while the maintenance value and angular-velocity magnitude are zero.
The typed record aliases that counter with the signed view used by `0x5779d0`,
preserving the underlying two bytes.

`tools/verify_world_object_maintenance.py` runs six cases through the original
callback and `0x6f1210` magnitude helper with `0x520c20` isolated; the byte-image
adapter now matches the complete `0x4f8` owner record for all six cases. The owned
`0x520c20` physics step is now separately translated in Python and C++. It
executes gravity projection, velocity integration or stop behavior, scheduler
force gating, and the stored kinetic-energy metric. Python and C++ each match
all 135 deterministic full-record original comparisons while isolating only
the step's `0x51e940` environment stage. A widened native run first exposed
ULP differences in zero-contact gravity projection: the C++ port retained
double products where the original stores each local gravity product before
its matrix sum. Those float32 product stores are now explicit. The `0x51e940` active success, empty-map, and correction-wrapper paths match 128 complete owner records using the translated `0x42e760` query with bounded grid, block, path, and geometry data. The original frame selector, side selector, geometry transform and plane math execute; only correction children `0x43ba40`/`0x43b750` remain isolated on that branch. A broader 1,200-case integration sweep now matches every owner byte exactly. Case 547 resolved an x87 precision boundary: the clearance caller subtracts the extended plane-height return before rounding the final store, unlike the separate `+0x34c` helper-result store. The translated `0x51fc00` six-contact pass and its
`0x457780` per-contact response execute in the Python and native paths. Direct
original comparisons cover 134 per-contact cases and 36 six-contact records;
the parent has 135 Python and seven curated native comparisons. This closes the
contact-force child boundary, while full collision/terrain behavior still
depends on unresolved correction children despite the now exact 1,200-case `0x51e940` bounded environment corpus. Its translated helpers `0x42df00`, `0x42e230`, `0x42e760` and fallback wrapper `0x43bfd0` now have bounded original comparisons; `0x43ba40`/`0x43b750` remain open. See
`client/world_object_physics_step.py` and
`tools/verify_world_object_physics_step.py`. Python and C++ each match all 135
deterministic cases; contact force is translated in both implementations. The
the correction-child and real-track coverage gaps remain open.

The adjacent scheduled entry `0x426730` has no Ghidra FunctionManager record, so
its complete 53-byte instruction range is retained separately in
`docs/recovery/supplemental-callbacks.json`. Its Python and C++ ports reproduce
the global array count, `0x4f8` row stride, active-byte test at `+4`, and ordered
dispatch to the required `0x520250` handler. Four original-executable cases
verify which rows dispatch. Four additional end-to-end cases run the live
`0x520250` child through the original dispatcher and compare all bytes of active
and inactive rows against `update_object_array`; the call site's provider
procedure identity is unknown, so it remains a supplemental bounded dispatch
observation rather than a Ghidra function entry.
After adding the matrix helper, the native suite passed 197/197 tests and the
full Python suite passed 1018 tests (7 skipped). Current totals are recorded
after the per-object update translation below.

## Math-library equivalent: 3x3 transpose

The per-object world update calls `0x6f12a0` to transpose a 3x3 matrix. Its
complete 61-byte body copies nine 32-bit words into transposed row-major order.
`client/matrix_math.py` and `native/src/matrix_math.cpp` preserve the words
without interpreting them as floats, including signed zero, infinities, NaNs and
other bit patterns. Three exact original-executable cases pass through the
bounded x86 oracle.

The same module implements the three-component dot product called by the object
update (`0x6f1140`/`0x6f3b51`). Four exact x87-result comparisons against the
original pass, including mixed signs and cancellation.

The original's periodic `0x5538a0` correction is now translated too. Its
ten-step call forms the Gram error matrix, evaluates the nine-term polynomial
with the client's coefficients, and applies the correction to the input
rotation. `0x6f2a60` is implemented as the alias-safe 3x3 product used by that
routine. Four exact matrix comparisons pass against the executable.

The `0x6f1320` geometry wrapper saves and restores its current matrix,
position, and vertex-count state around the mode-6 transform. Its state setters
also reproduce the observed dirty flags and cache invalidation. Mode 6 selects
the x87 vertex-transform path at `0x83a290`, which transforms 22 local vertices
into the object's world-vertex buffer with 12-byte input and output strides.
The exact matrix and position convention is translated in Python and C++.
Other `0x6f28f0` dispatch modes, CPU-optimized variants, and later GPU
presentation remain outside this bounded translation.

## Source translation: per-object motion and transform update

`0x520250` is now translated in Python and C++ for an active object record. It
preserves the object's world-space center of mass while integrating linear
velocity and turn-based angular velocity at 1/32-second steps, updates its
3x3 rotation, writes the transposed matrix and three projected values, then
transforms all 22 local vertices into the world-vertex buffer. Its recovered
input offsets are represented as named fields in `WorldObjectUpdate`.

`tools/verify_world_object_update.py` compares position, rotation, transpose,
projection outputs, and all 66 world-vertex floats against the installed
SHA-verified executable. Eight cases exercise both the ordinary path and the
periodic matrix-repair branch, including the original mode-6 transform. The
Python and native implementations match every checked output. The later GPU
presentation path remains an explicit boundary. The native suite passes 200
tests. The comparison was rerun against the installed executable during this
recovery pass and all eight cases passed. `0x520250` is now explicitly reviewed
in the generated function inventory; the 1,139-case Python suite was also run
at that checkpoint (seven skipped). Neither check validates rendering modes
other than the tested mode-6 transform or whole-game integration.
