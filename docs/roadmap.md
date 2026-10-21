# Roadmap

**Current priority:** reconstruct the actual Motor City Online client as coherent,
buildable source. [Source recovery](source-recovery.md) is the route to that game,
not a substitute deliverable. The playable prototype is a temporary comparison
harness and is not game completion.

The intended result is a playable, open-source Windows/Linux game client with modern OS compatibility. A renderer alone does not meet that goal.

Behavioral fidelity to Motor City Online is the target. Recover original systems
from executable and asset evidence, verify their behavior, and replace temporary
prototype systems with portable implementations. Prototype driving is a development
harness and does not define the intended handling or game rules.

## Implemented foundations

- Bounded archive, vehicle geometry, texture and base-track decoders.
- Portable stock catalogue and component interpretation.
- Windows OpenGL garage and textured vehicle/track scene.
- Body selection, component placement, tire/contact geometry and recovered motion updates.
- Independently verified portions of the engine dyno solver.
- Offline prototype driving with terrain support, steering, braking/reverse, pause/reset, ordered checkpoints and lap/sprint timing.
- Asset-free tests and Windows/Ubuntu CI configuration.
- Actual Linux OpenGL garage smoke check with generated geometry under Xvfb/Mesa.

## Immediate game reconstruction gates

1. Complete cylinder-state/thermodynamic integration and final engine-curve corrections, including unsupported fuel/boost branches.
2. Implement recovered tire forces, suspension forces, steering, drivetrain, braking and collision response.
3. Complete original owner startup and per-tick shared-state wiring; eliminate mandatory placeholder callbacks from the actual playable path.
4. Connect recovered force, collision and world-object updates using original input/configuration and terrain producers; replace bicycle dynamics. The `0x426730` active-object array plus live `0x520250` motion/vertex child now match full owner bytes in composed executable comparisons; `0x4265f0` now has a full-record adapter around its required `0x520c20` child. Scheduler, force, collision and playable-path integration remain open.
5. Reconstruct original game startup, screens, event/race state, audio and persistence, then exercise a complete offline game loop on installed assets.

These gates are substantial unfinished engineering. The prototype sprint is only
a geometry/input smoke harness; it is not evidence that the game has been
reconstructed.

## Work to reach a complete client

- Track objects/effects, materials, vehicle customization and sound.
- Local game progression and appropriate menus.
- Networking, login, economy and multiplayer services/protocols; no live original service compatibility is currently claimed.
- Windows and Linux graphics/runtime verification, controller input, packaging and installation.
- Performance profiling, malformed-content handling and broader vehicle/track validation.

## Mod development kit

Provide documented, versioned extension points and tooling for vehicle, component,
track and presentation add-ons. Include package validation, dependency/conflict
reports, examples, and a development workflow that does not modify original files.
See [the mod kit design](mod-dev-kit.md). Preserve recovered original behavior
as the default; make simulation changes explicit and negotiate online compatibility
once the target server protocol is understood.

## Completion evidence

Use real runtime checks for driving, audio, networking and rendering. CI passing synthetic tests does not prove these features. Linux CI now exercises the generated-geometry garage on Mesa; verify original-asset gameplay, hardware drivers and networking separately. A universal Python wheel alone does not establish runtime compatibility.
