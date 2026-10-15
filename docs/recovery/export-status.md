# Installation recovery export status

30 installed executable-signature/extension candidates; 29 unique hashes.

Header scanning includes ASI plugins and extensionless cache files. Non-executable
extension candidates and historical cache copies are labeled separately.

| Installed paths | Role | Enumeration | Entries | Decompiled | Failed/timeout | Not attempted |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 3dSetup/3DSetup.dll | installation | ghidra-export | 1365 | 1143 | 0 | 0 |
| 3dSetup/3DSetup.exe | installation | ghidra-export | 2885 | 2367 | 0 | 0 |
| Compress.dll | installation | ghidra-export | 14 | 9 | 0 | 0 |
| Data/Text/phid.exe | installation | not-native-executable | — | 0 | 0 | — |
| dinput8.dll | installation | ghidra-export | 6539 | 6316 | 0 | 0 |
| dx7z.dll | installation | ghidra-export | 186 | 148 | 0 | 0 |
| dx8z.dll, dx8zDB.dll | installation | ghidra-export | 300 | 258 | 0 | 0 |
| IFC22.dll | installation | ghidra-export | 899 | 816 | 0 | 0 |
| IMPLODE.DLL | installation | ghidra-export | 67 | 53 | 0 | 0 |
| ip.exe | installation | ghidra-export | 2377 | 1991 | 0 | 0 |
| mcity.exe | installation | ghidra-export | 25773 | 25434 | 1 | 0 |
| mco-launcher.exe | installation | ghidra-export | 4348 | 4042 | 2 | 0 |
| nps/authlogin.dll | installation | ghidra-export | 496 | 416 | 0 | 0 |
| nps/mco.exe | installation | ghidra-export | 2985 | 2795 | 0 | 0 |
| nps/mrbupd.dll | installation | ghidra-export | 589 | 480 | 0 | 0 |
| nps/NPSAnlyz.dll | installation | ghidra-export | 54 | 36 | 0 | 0 |
| nps/PBA.exe | installation | ghidra-export | 178 | 76 | 0 | 0 |
| nps/ProxyTool.exe | installation | ghidra-export | 186 | 58 | 0 | 0 |
| scripts/DAO/dao350.dll | installation | ghidra-export | 1571 | 1472 | 0 | 0 |
| scripts/DAO/msjet35.dll | installation | ghidra-export | 3693 | 3560 | 0 | 0 |
| scripts/DAO/msjint35.dll | installation | ghidra-export | 60 | 34 | 0 | 0 |
| scripts/DAO/msjter35.dll | installation | ghidra-export | 84 | 54 | 0 | 0 |
| scripts/MCOExOps.asi | installation | ghidra-export | 223 | 147 | 0 | 0 |
| scripts/MCOWidescreenMod.asi | installation | ghidra-export | 564 | 439 | 0 | 0 |
| softtriz.dll | installation | ghidra-export | 374 | 307 | 0 | 0 |
| Stage/.castanet/undo/40/287 | historical-cache | ghidra-export | 290 | 260 | 0 | 0 |
| Stage/.castanet/undo/40/290 | historical-cache | ghidra-export | 23092 | 22755 | 0 | 0 |
| Uninst.dll | installation | ghidra-export | 205 | 141 | 0 | 0 |
| voodoo2z.dll | installation | ghidra-export | 120 | 90 | 0 | 0 |

Decompiled means private pseudocode was exported, not translated or buildable source.
External imports are separate from attempted internal functions. Failed and timed-out
entries remain in each module inventory. Old REA records remain separately indexed in
[the reviewed main-executable worksheet](status.md); zero new exports does not erase them.
Only metadata is published. Runtime behavior and function boundaries remain unverified.
