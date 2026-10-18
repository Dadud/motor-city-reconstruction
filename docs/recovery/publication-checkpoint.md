# GitHub publication checkpoint

The October 18, 2026 update publishes the current verified source tree as a single fast-forward snapshot after GitHub baseline `e34e280`. Existing published history is preserved. Detailed unpublished recovery checkpoints remain available locally on branch `local-checkpoints/pre-github-2026-10-18`; they were consolidated for publication because their 24 generated corpus versions total about 6.6 GB, with individual JSON blobs above GitHub's normal Git file limit. This is a packaging change, not a loss of authored source or retained current observations.

The current synthetic original/native corpus is stored through Git LFS at `docs/recovery/corpora/wave0.json`. Run `git lfs install` and `git lfs pull` after cloning. The Python/native comparison CI jobs explicitly fetch LFS data. Original executables/assets and private decompiler exports remain external and are not published.

This update includes the startup controller and its recovered input/cleanup connections, keyboard/mouse/window and camera recovery, device information/acquisition/lifetime, queue and translation behavior, shared layouts and callback aliases, corpus tooling, installation inventories and function-review evidence. It remains a partial reconstruction. Complete linked Windows/Linux game builds and gameplay acceptance are unfinished.

The local checkpoint sequence preceding the startup/publication batch is retained below for provenance. These unpublished hashes describe the local archive, not separate commits on GitHub's published main history.

```text
f8e7a93 Translate original per-gear force table producer
03e5dc6 Translate original model part preparation and reference alignment
893339e Translate original startup force helper and acceleration tables
e6856fc Track reviewed recovery packages and installation work index
e92f1a6 Identify the acceleration-table producer caller in owner binding
2e29fba Pin the startup record layout in the owner-binding caller
813ff4e Translate the startup record constructor 0x53a1f0
f3215d2 Cover the NULL-model default-axle branch in the startup record oracle
8ee8205 Port the startup record constructor to native and compare it bit-for-bit
74d7d97 Add rule-based function triage across all inventoried binaries
6536fe3 Add the recovery cell factory and disposition the linker-artifact region
7e8c516 Publish the required-function denominator and complete Phase 0
99e9abf Complete the cell factory and scaffold the first recovery cell
8002eba Resolve the scene_area argument question and characterize the body
ff9a9c9 Track factory provenance so manifest edits regenerate safely
2d883ca Add the shared layout registry with source drift auditing
c009b92 Complete Phase 2: shared layout registry with attribution and drift audit
53955e2 Execute the first wave-0 recovery cell end to end
ce57989 Report wave execution progress in the triage summary
00384d7 Add a shared cdecl call stub to the oracle, with its emulator limits pinned
e2d8570 Execute two more wave-0 cells through the verified call stub
0b70c44 Execute the entity flag predicate as the fourth wave-0 cell
b749ffd Execute the registry registration cell as the fifth wave-0 recovery
3b713d5 Execute the inverted entity predicate as the sixth wave-0 recovery
68fa11b Execute the wave-0 pure leaf batch: eight cells in one verified pass
a1cdb0f Execute the wave-0 registry and buffer batch: eight more cells
1d9896a Add the pseudocode-first pipeline and recover six more wave-0 cells
416bdd2 Connect native recovery cells to original observations and restore portable builds
8c2a8df Recover record-stack utilities with instruction-ordered copies
4086969 Recover record transition controllers and verify callback lifecycles
3f225cc Recover register-based selection state normalization
d5aadaf Recover camera preset application and connected selection lifecycle
929f938 Recover camera preset cycling and explicit mode transitions
6a236aa Recover raw key queries, press latches and key-release producer
a804518 Recover keyboard queue producers and connected input lifecycle
ec8baf6 Recover camera matrix rotations with original comparisons
ce57279 Recover track spatial lookup and connected input-to-camera path
90a2180 Recover initialized window dispatch through keyboard and camera
dda9349 Recover character and initialized mouse input paths
5acdc2c Recover scan translation and connected queue consumption
0a5f659 Connect device acquisition to scan translation and queue consumption
09246ab Recover device information enumeration and persistent state access
6e64410 Recover device initialization and cleanup lifetime paths
a791920 Share device globals and integrate evidenced function supplements
d16ea11 Verify initialization-to-input sessions against original execution
3ffdfc5 Share callback identity with overlapping scan lookup bytes
e0c6163 Recover full-return callback dispatch and byte-masked fallback
a81ceac Recover default queue callback and overlapping key action router
b5e141f Verify full initialization through default action sessions
8afbd81 Recover console input core and verify game fallback sessions
5420b12 Audit action-table references and identify cleanup registry dependency
a4994b3 Recover cleanup registry and connect device shutdown lifecycle
49fd7b7 Recover keyboard layout selection and shared scan remapping
```
