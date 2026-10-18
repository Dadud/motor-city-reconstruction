# Copied original startup reference

On 2026-10-18 a hash-pinned private copy of mcity.exe and shipped data/DLLs was launched through REA 6.7.0/Frida. Original account saves, scripts and mods were excluded. Hooks were installed before resume. API-level network/child guards and original-directory write guards were active; these do not provide OS network isolation. Dialogs returned synthetic IDCANCEL.

Both eight-second probes reached the PE entry and shared cleanup, but did not reach recovered input startup. The original client displayed a critical-files/administrator-privileges error. Probe 02 observed MessageBoxA caller `0x5344e7`; no CreateFile failure was observed by the bounded hooks. The precise triggering resource/check remains unresolved. No blocked network API call was observed.

Tools: `tools/original_startup_probe.py`, `tools/rea_stdio.py`, `tools/fixtures/mco_offline_startup.js`. Full runtime results and copied binaries remain private under ignored evidence. This is original-client reference evidence, not reconstruction acceptance.

Probe 03 observed `RegOpenKeyExA` on `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\mcity.exe` returning Windows error 5 (access denied), caller `0x51d38b`, immediately before the same error dialog. The requested access mask and required values remain to be established; this is a concrete candidate for the early-exit cause, not yet causal proof.
