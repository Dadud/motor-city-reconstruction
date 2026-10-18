# Copied original startup reference

On 2026-10-18 a hash-pinned private copy of mcity.exe and shipped data/DLLs was launched through REA 6.7.0/Frida. Original account saves, scripts and mods were excluded. Hooks were installed before resume. API-level network/child guards and original-directory write guards were active; these do not provide OS network isolation. Dialogs returned synthetic IDCANCEL.

Both eight-second probes reached the PE entry and shared cleanup, but did not reach recovered input startup. The original client displayed a critical-files/administrator-privileges error. Probe 02 observed MessageBoxA caller `0x5344e7`; no CreateFile failure was observed by the bounded hooks. The precise triggering resource/check remains unresolved. No blocked network API call was observed.

Tools: `tools/original_startup_probe.py`, `tools/rea_stdio.py`, `tools/fixtures/mco_offline_startup.js`. Full runtime results and copied binaries remain private under ignored evidence. This is original-client reference evidence, not reconstruction acceptance.

Probe 03 observed `RegOpenKeyExA` on `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\mcity.exe` returning Windows error 5 (access denied), caller `0x51d38b`, immediately before the same error dialog. The requested access mask and required values remain to be established; this is a concrete candidate for the early-exit cause, not yet causal proof.

Probe 04 established requested access `0xF003F` (`KEY_ALL_ACCESS`) for the App Paths key; the key is readable by the current unelevated process. Probe 05 substituted `KEY_READ` only for that exact key: its open succeeded, then the exact `SOFTWARE\Electronic Arts\Motor City\1.0` key failed with the same excessive access request. Probe 06 substituted read-only access for both exact install keys: both succeeded and the critical-files dialog was absent. The client proceeded to the `SOFTWARE\Electronic Arts\Network Play System` lookup, which returned error 2 (not found), then Frida reported detached before input startup. This identifies the excessive access requests as blockers for the earlier dialog; the next detach cause is still unproven.

No registry edits or elevation were performed. The optional `--registry-readonly` switch labels this controlled substitution. Original-directory working-directory changes are redirected to the private stage. The target stop attempt after detached runs returned Windows error 87 and is recorded explicitly; this tool result does not prove target lifetime cleanup by itself.
