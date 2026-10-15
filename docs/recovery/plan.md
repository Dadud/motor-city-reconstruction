# Approved source recovery plan

The current deliverable is readable, organized source for the existing game with
a repeatable Windows/Linux build. New features and mod-kit expansion are deferred.
Decompiler output is private research material, not original source or a working
build. Authored code remains in the existing MIT repository; original assets and
binaries remain external and read-only.

1. Inventory installed executables and DLLs recursively: hashes, functions,
   imports/exports and dependencies. Separate game code, bundled libraries,
   runtime code and patches through reviewed classifications.
2. Export available decompilation into private, resumable research files. Preserve
   analysis databases, tool profiles, failure records and uncertain boundaries.
3. Recover shared types, classes, globals, calling conventions, ownership and
   cross-module interfaces. Preserve original address mappings and unknown fields.
4. Review every function: bounded translated, partial, decompiled only, missing/
   blocked, or identified library/runtime with a justified equivalent. Link code,
   evidence, dependencies, checks and unresolved branches.
5. Translate and connect in dependency order: utilities/formats; assets/databases;
   assembly; simulation; rendering/audio/input; menus/game flow; networking.
   Reuse verified implementations and never replace unknown behavior with invented
   gameplay. Keep optional prototypes separate from recovered client acceptance.
6. Extend the C++20/CMake build and `build.py` through subsystem builds to a linked
   client. Pin dependencies, document clean setup, establish Windows first and
   complete Linux platform adapters without changing recovered game behavior.
7. Compare bounded calculations and state changes against original execution,
   then verify integrated startup, assets, garage, driving, races and networking.
   Track compilation, original behavior and live fan-server acceptance separately.

Milestones: complete inventory; decompilation export/failure list; reviewed coverage
and shared types; compiling recovered subsystems; linked client loading original
assets; verified original game flows.

Completion requires every inventoried entry to have a reviewed disposition, every
required function to have an implementation or justified equivalent, clean-checkout
builds on Windows/Linux and passing documented gameplay acceptance scenarios.
No percentage is inferred from decompiled-function counts. Required mismatches and
unverified online behavior remain visible until resolved.
