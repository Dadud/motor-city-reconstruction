# Copied original startup reference

The copied reference client has two distinct early paths. Unelevated registry opens request excessive write access and produce the critical-files dialog. After controlled read-only substitution for the two exact install keys, direct launch takes the launcher handoff branch and exits normally. The absent Network Play System registry key controls optional logging; it is not evidence of a required runtime dependency or the cause of this exit.

## Observed runtime evidence

Private probes ran the SHA-pinned mcity.exe (`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`) through REA 6.7.0/Frida on 2026-10-18. Each observed eight seconds. Shipped data/DLLs were copied; original account saves, scripts and mods were excluded. No original registry values were changed and no elevation was used.

- Probes 03–04: `RegOpenKeyExA` requests `0xF003F` (`KEY_ALL_ACCESS`) for `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\mcity.exe`; Windows returns error 5. The same key is readable by the current process. Dialog caller: `0x5344e7`.
- Probe 05: `KEY_READ` substitution makes that open succeed; the exact `SOFTWARE\Electronic Arts\Motor City\1.0` key then fails with the same excessive request.
- Probe 06: substituting read-only access for both exact install keys removes the critical-files dialog. The Network Play System key returns error 2; Frida then detaches before recovered input startup.
- Probe 07: retained owned-process handle confirms actual process exit code 0. `ExitProcess` caller is `0x69c26c`. No DLL-load failure or target exception is observed by the bounded hooks.
- Probe 09 control (same observation hooks, no access substitution): the installation check returns 1 and the critical-files dialog reappears; the process exits with code 0. This preserves the baseline failure independently of the handoff probe.
- Probe 08: actual launcher atom parser `0x523ed0` returns 0; installation check `0x530790` returns 0; `WinExec` is intercepted at caller `0x52436d`; WinMain `0x5241f0` returns 0. Thus direct launch takes the launcher handoff, rather than entering graphics/input startup. The attempted child is blocked and no command-line credential values are captured.

Full results remain private under `evidence/original-startup-offline-20261018/probe-01` through `probe-08`. Probe 08 script SHA-256: `097522ff145635e0943417cae2c67490fe91c17d7a75901cb5d0308f91431dbc`. Prior stop attempts after process exit returned Windows error 87; subsequent probes retain the spawned process handle and distinguish already-exited state from forced termination without relying on a reusable PID.

## Primary static confirmation

Ghidra 12.1.4, target SHA above, batch analysis profile `71d7ca265fa4ce13787c44df478e19d5e53d867f56db0648321f11364213ffcd`:

- `ev_187bc9ccf772d1215142971cc0927676867dc56622ba2ab235abf9e7a7bb1627`: `0x718d40` sets a logging-enable field from the optional registry value and continues regardless of the absent key. Also confirms registry constructor/reopen/language helper pseudocode.
- `ev_ad498686d6aed10926f7d86e7c59efd9a0e7a535b4e5bcfb167131bd6324db5b`: WinMain invokes the atom parser, performs install checks, initializes logging, and calls WinExec for nps_MCO.exe when the parser result is zero. Atom parsing consumes two Windows global atoms; no live atom values were supplied or read by the investigation.

These are resolved pseudocode results, not complete-body ownership claims. Full bundle and compatible snapshot: ignored `evidence/install-startup-primary.*`.

## Scope and next work

`tools/original_startup_probe.py` loads `tools/fixtures/mco_offline_startup.js` before resume through a fresh `tools/rea_stdio.py` session. API-level socket, child-process and original-directory write guards are active; WinExec is separately intercepted because blocking exported CreateProcess does not establish WinExec interception. Original-directory working-directory changes redirect to the private stage. Dialogs return synthetic IDCANCEL. These controls are not OS network isolation.

The optional `--registry-readonly` flag labels the controlled access substitution. Neither that substitution nor the direct-launch reference proves launcher-authenticated startup, renderer/hardware behavior, account connectivity or a playable reconstruction. Continue implementing the recovered install/startup interfaces against synthetic inputs; actual launcher authentication and game startup remain open.
