# Renderer capability and vertex-format state

Three small client routines update shared renderer globals:

- `0x6f19d0` replaces the first cached capability word, marks its dirty word
  when the requested value is nonzero, and invalidates the render-mode cache
  when the requested value is zero.
- `0x6f1a00` does the same for the second capability and its dirty word.
- `0x6f1a70` replaces the vertex-format cache and invalidates the render-mode
  cache only when the new format is zero.

`RenderCapabilityState` and its setter functions represent these transitions
without depending on process globals. `tools.verify_render_capability_state.py`
compares each direct native call's return value and all six relevant globals
over 512 cases per entry, including zero, one, and randomized uint32 values.
All 1,536 comparisons match exactly. Device interaction and higher-level mode
selection remain outside this state-setter scope.

Static provenance: retained Ghidra 12.1.4 pseudocode and native bodies from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
