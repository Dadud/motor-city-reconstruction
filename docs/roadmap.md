# Roadmap

The intended result is a playable, open-source Windows/Linux game client with modern OS compatibility. A renderer alone does not meet that goal.

## Implemented foundations

- Bounded archive, vehicle geometry, texture and base-track decoders.
- Portable stock catalogue and component interpretation.
- Windows OpenGL garage and textured vehicle/track scene.
- Body selection, component placement, tire/contact geometry and recovered motion updates.
- Independently verified portions of the engine dyno solver.
- Offline prototype driving with terrain support, steering, braking/reverse, pause/reset, ordered checkpoints and lap/sprint timing.
- Asset-free tests and Windows/Ubuntu CI configuration.
- Actual Linux OpenGL garage smoke check with generated geometry under Xvfb/Mesa.

## Work to reach driving

1. Complete cylinder-state/thermodynamic integration and final engine-curve corrections, including unsupported fuel/boost branches.
2. Implement recovered tire forces, suspension forces, steering, drivetrain, braking and collision response.
3. Replace prototype driving parameters with verified forces; retain the working input, fixed-step scheduling, scene pose, pause/reset and race UI.
4. Finish tire sizing, suspension stance and nested component assembly.
5. Broaden controllable driving and stability checks beyond the verified Drag sprint and Boothill start.

## Work to reach a complete client

- Track objects/effects, materials, vehicle customization and sound.
- Local game progression and appropriate menus.
- Networking, login, economy and multiplayer services/protocols; no live original service compatibility is currently claimed.
- Windows and Linux graphics/runtime verification, controller input, packaging and installation.
- Performance profiling, malformed-content handling and broader vehicle/track validation.

## Completion evidence

Use real runtime checks for driving, audio, networking and rendering. CI passing synthetic tests does not prove these features. Linux CI now exercises the generated-geometry garage on Mesa; verify original-asset gameplay, hardware drivers and networking separately. A universal Python wheel alone does not establish runtime compatibility.
