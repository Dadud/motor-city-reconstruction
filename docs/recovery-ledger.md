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

| Feature | Current status and evidence | Remaining recovery path | Acceptance scenario |
| --- | --- | --- | --- |
| Startup and asset discovery | Partial: explicit read-only asset root, bounded VIV reads and case-insensitive lookup; `assets.py`, `tools/viv.py` | Recover required startup resources and original loading/failure sequence; migrate platform startup | Start from a fresh installation on Windows and Linux; missing/corrupt required assets produce an actionable error without modifying originals |
| Vehicle geometry and textures | Partial: [native FCE/FSH garage](native-garage.md); 315 original archives/99,608 positions and 254 texture image checksums match Python, original textured renders pass on Windows | Unsupported codecs, authentic materials/paint, attachment visibility, stock assembly and animation | Decode installed vehicle corpus; compare representative assembled cars to original views and reject malformed content safely |
| Tracks and world presentation | Partial: base track meshes, spatial lookup and support; `track*.py`, `world.py` | Objects, effects, material/render ordering, visibility and full track variants | Traverse every supported track with original assets; compare landmarks, surfaces and object placement |
| Catalogue and stock assembly | Partial: typed catalogue, physics fields and component interpretation; `catalogue.py`, `assembly.py`, `physics_data.py` | Resolve unsupported assemblies, conversion cases, dimensions and nested placement | Assemble stock corpus with explicit reports for every rejected record; compare complete geometry and component inputs |
| Owned and modified vehicles | Partial: enrichment/discovery and verified insertion, pruning, ordering, linking and numeric totals connected in the [postload sequence](owned-postload.md); [outer descriptions](calculations/owned-component-descriptions.md) retain explicit leaf/localization inputs | Recover part-specific descriptions and localized labels, complete DB loading/handoff, mechanical aggregates and online refresh; verify integration on actual owned cars | Load an actually modified owned car without stock substitution; compare complete hierarchy, attachments and derived values |
| Engine calculations | Partial: standalone unboosted nineteen-knot core matches 46 complete original records; integration matches 44,635 original steps; [engine](calculations/engine-dyno.md), [cycle](calculations/cylinder-cycle.md) | Boost, native abort semantics, final curve corrections and wider domain coverage | Compare full engine curves and intermediate state for supported stock and modified engines, including boundary modes |
| Motion and support geometry | Recovered bounded calculations: pose updates and contact geometry; [motion](calculations/vehicle-motion.md) | Confirm full call ordering, units, wheel sizing and stance in the integrated simulation | Original versus reconstruction pose/contact traces agree under documented tolerances and identical inputs |
| Tire/suspension/drivetrain/brake forces | Partial: recovered tire dimensions, spring/shock validation and `simulation_inputs.py` stock bridge wired into `world.py`; full integrated force model unknown | Trace original force producers, steering, gears/clutch, differential, surface and aero consumers | Match original acceleration, gear changes, braking, skid and cornering scenarios for multiple configurations |
| Collisions | Unknown complete object/vehicle response | Recover broad/narrow phase, contact impulses, damage, recovery and update order | Compare track-object and vehicle collisions, resting contacts and post-impact behavior |
| Offline driving | Prototype: authored 120 Hz terrain-following bicycle model; `driving.py` | Replace forces only after original calculations are verified; retain harness for comparison | Recovered model passes repeated original driving scenarios with reproducible outcomes |
| Race rules and results | Prototype: inferred course closure and ordered gates; `racing.py` | Recover actual event definitions, start/finish rules, penalties, standings and result consumers | Original-equivalent starts, checkpoints, finish classification and timing across event types |
| Garage and customization UI | Partial garage preview and body/component presentation | Recover menus, part installation/removal, paint/material changes, validation and state transitions | Complete garage editing flow renders and persists the selected configuration correctly |
| Shops, repairs and economy | Partial recovered part valuation; [valuation](calculations/owned-part-valuation.md) | Recover transaction builders, replies, inventory changes, limits and rejection handling | Purchase, install and repair scenarios match original values and server-confirmed state; rejected requests leave state consistent |
| Progression | Unknown complete flow | Recover profile/event/progression consumers and authoritative updates | Race rewards and unlocks survive restart and agree with server/original account state |
| Account and personas | Partial: blocking orchestration plus private [account check](online-account.md) and [fan-server flow check](fan-server-testing.md) through login, persona list, lobby, primary MCOTS and optional garage startup; [startup key value](nps-key-initialization.md) matches nine bounded original cases; live acceptance unverified | Asynchronous lifecycle, playable UI, reconnect and documented live MotorCity Revival runs | Authorized account logs in, selects persona, connects lobby and primary, loads garage counts on both platforms; denial/cancellation expose no secrets |
| Lobby and chat | Partial: transport/login/channel/send recovery plus room validation; [channel codec](lobby-channel-codec.md) reproduces `0x106` payloads and `0x214`/`0x215` reply fields in bounded native comparisons (27 payloads, nine capacity rejections, six reply cases); live room join and race channel not implemented | Recover authenticated room argument construction, channel lifecycle, game-network task dispatch integration, presence/chat UI and reconnect behavior | Join actual lobby, add a room channel, exchange supported messages and reconnect with consistent presence |
| Primary game data | Partial: encrypted/compressed session, paged fetching and persona startup sequence (0xac/0x6c/0x108) exercised by fan-server check; [session](mcots-session.md), [data](post-login-data.md) | Additional service joins, complete owned-car assembly, background dispatch and unsolicited 0x198 handling in a playable client | Load live owned modified car data with optional catalogue enrichment; process unsolicited updates without losing synchronization |
| Online race and synchronization | Partial: static channel/task evidence plus `race_entry.py` local task construction probe and `online_sync.py` declared update-rate/transport settings surfaced in fan-server check; live room join and position sync not implemented | Recover authenticated room negotiation, game-start dispatch, peer sync, corrections, disconnects and finish reporting | Join and finish a supported fan-server race with correct remote motion and persisted results |
| Audio | Unknown complete implementation | Inventory sound formats and recover sound selection, engine/load transitions, mix and lifecycle | Original-equivalent engine, tire, impact, interface and music behavior on both platforms |
| Settings and input | Partial keyboard/display preferences; `settings.py`, `app.py` | Controller mappings, configurable controls, audio/display persistence and focus handling | Keyboard/controller driving, focus loss and settings persistence work on both platforms |
| Native runtime | Partial calculation ports, bounded Lua and [original-geometry garage](native-garage.md); native driving/online unknown | Follow [native migration](native-migration.md), preserving comparison fixtures | Reproducible Windows/Linux packages run real original-asset gameplay without Python, REA or Ghidra |
| Mod kit | Partial [working data alpha](mod-kit-tutorial.md): six resource kinds, manifests, dependencies, explicit overlays and four tools; [Lua alpha](mod-lua-alpha.md) supports directory/ZIP packages, reproducible archives and real bounded native registration/inspection through `tools.modkit script` | Native game resource loading, supported gameplay events/state, script dependencies/replacements and complete compatibility documentation | Outside developer creates, validates, packages and runs a content/script mod using published instructions |

## Ordered gates

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
