# REA workflow audit and operating contract

Audit date: October 18, 2026. Upstream: https://github.com/morluto/rea at `23f984b1a884baefc3c44e4ab697f6eff61dffb6` (package 6.7.0, skill revision 42). Upstream main can change independently of installed releases; active schemas and the matching bundled skill govern available operations.

## Verified setup

The initial CLI and connected MCP server were 6.4.0 with skill revision 37 and 170 tools. The supported `rea update` workflow installed and verified CLI 6.7.0. A scoped setup plan updated only Codex's REA registration and the shared skill. The applied plan reported ready and healthy. A recovery backup exists for the previous Codex config; unrelated parsed configuration is unchanged. Ghidra's path is unchanged and Java's path was normalized to Windows separators but resolves to the same JDK directory. No analysis engine or unrelated prerequisite was installed.

The installed skill is revision 42 with generated tool count 207. Its text matches the inspected upstream skill after removing the generated count and pinning upstream `@latest` examples to `@6.7.0`, as the release installer does. Node is 24.21.0; the functioning native provider is Ghidra 12.1.4 with the existing JDK 21 installation.

The active Codex MCP connection still reports 6.4.0. An explicit `binary_session(expected_package_version="6.7.0")` check returned `mcp_server_restart_required` / `package_version_mismatch`. Reconnect REA or restart Codex, then verify actual server identity before treating MCP as 6.7. Until that happens, native work uses the verified 6.7 CLI with the existing registered provider environment. Updating files on disk alone does not establish live-server alignment.

## Executed native verification

A preserved copy of the old `mcity-native.snapshot.json` was rejected with `evidence_integrity_mismatch` / analysis snapshot validation failure. The reason does not establish that all older Evidence is invalid or that a specific version caused the failure. The original snapshot and rejected copy remain byte-identical; no validation was bypassed. A fresh private snapshot and complete function Evidence were then produced successfully through the 6.7 CLI.

- Target: `mcity.exe`, SHA-256 `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
- Operation: `analyze_function`, selected entry `0x6bfa10`.
- Evidence: `ev_efec5513eb8548562dc9f2b0ae2ae62669ecfc753bcbd49851053d8acc887943`.
- Provider: Ghidra 12.1.4; profile digest `3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.
- Body observation: one inclusive range `0x6bfa10..0x6bfc56`, 583 bytes, non-contiguous false.
- Authority/confidence: shipped-artifact / observed, describing static database facts.
- Full private record: `evidence/rea-audit-6.7-startup-fresh.json`; fresh snapshot: `evidence/rea-6.7-native.snapshot.json`.

The record supplies pseudocode, assembly, CFG and references. Its complete call-relationship status covers resolved Ghidra references; computed/indirect targets remain unknown where not established. PDB metadata mentions MCity.pdb with load state unknown, so missing names/types are not absence evidence. Windows metadata mutation and other unavailable operations must be checked in the active provider's tool availability rather than assumed supported.

CLI calls must inherit the configured `GHIDRA_INSTALL_DIR` and `JAVA_HOME` values; MCP registration environment is not automatically present in an ordinary shell. The successful test forwarded those existing values into a child process without changing global environment settings.

This static check supplements the existing bounded original-instruction/native comparisons. It does not establish native game startup, real platform calls or whole-client equivalence.

## Workflow corrections

1. Primary binary questions use REA function/API/instruction/reference facts, then focused retained views. Keep Evidence IDs, target/provider/profile identities and limitations with conclusions.
2. Saved compatible observations are reusable; never claim they are a currently open/live session. On identity changes, validate once and diagnose the actual mismatch. Do not repeatedly run setup or reanalyse the entire executable.
3. Capstone and Unicorn remain explicitly secondary tools. Preserve their independent value without relabeling them REA output. Synthetic bridge behavior is fixture scope, not recovered OS implementation.
4. Complete body AddressSets govern instruction ownership. The action-table helper previously labeled entry-plus-body-count windows contiguous bodies without establishing that fact. Its report and investigation now explicitly mark sampled windows, possible overlap/omitted ranges and unknown owned-body coverage. Its three literal hits remain observations in those windows; function-level absence is unproven.
5. Use summary/paged views instead of repeating producers or printing full catalogs. The first session-status response was unnecessarily large; subsequent inspection selects stored fields. Complete private records remain available.
6. Keep a question/Evidence/unknown ledger. Use supported REA unknown tracking and finite reconstruction-verification contracts when the current connection supports them. A passing local test suite does not close unrelated inventory or gameplay requirements.

The remaining setup action is MCP reconnection and identity verification. Broader reconstruction remains unfinished; this audit does not certify every historical inference or all REA capabilities on Windows.
