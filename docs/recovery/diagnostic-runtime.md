# Diagnostic runtime recovery

Five complete routines from the original mcity.exe are recovered as a connected package:

| Original | Recovered entry |
| --- | --- |
| 0x6bedf0 | diagnostic_initialize |
| 0x6bf1e0 | diagnostic_channel_configure |
| 0x6bef20 | diagnostic_device_configure |
| 0x6bf220 | diagnostic_channel_bits |
| 0x6bef70 | diagnostic_device_bits |

Primary static source is the retained REA Ghidra export under the private target-SHA directory `evidence/recovery-export/28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, its per-function pseudocode and direct-callee inventory. Target SHA-256 is that directory name. This package does not infer contiguous function ownership from body-byte counts.

The startup initializer now has a concrete diagnostic initialization implementation available to its subsystem dispatcher. It preserves the early initialized flag (which breaks recursive initialization), eight device and 64 channel flag updates, the exact metadata-clearing subranges, channel 2 enable, then conditional device 1 enable. Channel selector 0 updates all channels, selector 1 only channels with bit 1 set, other selectors update one channel. Channel enable uses boolean nonzero; device enable uses the argument low bit. A null device callback suppresses initialization and environment lookup entirely.

The representation is a named private working image of globals 0x8c4730..0x8c49af, not an inferred original C++ struct. Out-of-range selectors throw rather than exposing original unchecked writes. Admitted original domain is channel selectors 0..63 and device selectors 0..7.

Environment lookup 0x699e80 and configuration parsers 0x6bf2b0 / 0x6befa0 remain explicit platform boundaries. No parser implementation or real environment/Windows execution is claimed. Boundaries can mutate the live state and the wrappers retain original call ordering. Further recovery can replace these boundaries without changing core state storage.

`tools/diagnostic_runtime_cases.py` executes the five actual original routine bodies with the hash-checked Unicorn oracle. Only the environment lookup and parser entries are substituted. The 1,188 cases compare all 160 image words, initialized flag and boundary order/arguments. Domains include zero/nonzero initialized states, channel broadcast/selection, all eight devices, odd/even/noncanonical enable values, null device callbacks and environment absent/present with parser mutation. Native MSVC and Zig C++20 comparisons passed every case. This is bounded synthetic instruction evidence, not live Windows startup acceptance.

Integration: add a `diagnostic_runtime` implemented cell with the five roots above and use `capture(oracle)` from the cases module. Native comparator target and standard corpus replay module are supplied. Wire startup identity 0x6bedf0 to `diagnostic_initialize` and retain a DiagnosticRuntime alongside the existing startup/input state. No aggregate corpus, inventory or cell manifest was edited by this worker.

Primary REA confirmation: batch evidence `ev_da4c57797f8fda743887b42718d151ca08091a04f7848b5711db5c3943bc2581`, Ghidra 12.1.4, batch profile `71d7ca265fa4ce13787c44df478e19d5e53d867f56db0648321f11364213ffcd`. Five resolved procedure pseudocode results; this batch does not establish complete body ownership ranges. Full bundle and compatible snapshot remain private under `evidence/diagnostic-runtime-primary-rea.*`.
