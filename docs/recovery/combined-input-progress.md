# Combined input and diagnostic startup

The `combined_input_lifecycle` probe connects recovered startup, diagnostic initialization, mouse initialization, keyboard initialization/layout, NumLock, keyboard transitions, mouse geometry/reporting and shared reverse cleanup/restart. Fourteen persistent 18-step traces execute original x86 instructions with synthetic returning COM, OS, environment and parser boundaries. Both MSVC and Zig comparisons pass.

The original storage aliases are preserved: the keyboard translation image at `0x8c8748` includes mouse mode/state words at byte offsets 460, 464 and 468 and the callback at 476. `InputSharedTables` exposes a word-backed byte image without C++ aliasing violations.

This is a connected synthetic input probe. Renderer, operating system, hardware and full game startup remain unverified. Diagnostic environment/parser calls remain declared boundaries.
