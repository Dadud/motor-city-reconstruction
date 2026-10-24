# Installation work index

Generated from the existing module inventories and explicit review records.
Module roles describe investigation scope; they do not certify library equivalence.
Function counts are not a whole-game completion percentage.

| Installed paths | Role | Entries | Reviewed | Direct-call components |
| --- | --- | ---: | ---: | ---: |
| 3dSetup/3DSetup.dll | installation-tool | 1,365 | 0 | 1,356 |
| 3dSetup/3DSetup.exe | installation-tool | 2,885 | 0 | 2,875 |
| Compress.dll | compression-library-investigation | 14 | 0 | 14 |
| Data/Text/phid.exe | non-executable-data | 0 | 0 | 0 |
| dinput8.dll | patch-or-launcher-investigation | 6,539 | 0 | 6,507 |
| dx7z.dll | graphics-library-investigation | 186 | 0 | 186 |
| dx8z.dll, dx8zDB.dll | graphics-library-investigation | 300 | 0 | 299 |
| IFC22.dll | input-library-investigation | 899 | 0 | 884 |
| IMPLODE.DLL | compression-library-investigation | 67 | 0 | 67 |
| ip.exe | online-support-investigation | 2,377 | 0 | 2,367 |
| mcity.exe | game-client | 25,779 | 341 | 25,722 |
| mco-launcher.exe | patch-or-launcher-investigation | 4,348 | 0 | 4,260 |
| nps/authlogin.dll | online-support-investigation | 496 | 0 | 481 |
| nps/mco.exe | online-support-investigation | 2,985 | 0 | 2,969 |
| nps/mrbupd.dll | online-support-investigation | 589 | 0 | 586 |
| nps/NPSAnlyz.dll | online-support-investigation | 54 | 0 | 54 |
| nps/PBA.exe | online-support-investigation | 178 | 0 | 178 |
| nps/ProxyTool.exe | online-support-investigation | 186 | 0 | 186 |
| scripts/DAO/dao350.dll | database-library-candidate | 1,571 | 0 | 1,556 |
| scripts/DAO/msjet35.dll | database-library-candidate | 3,693 | 0 | 3,398 |
| scripts/DAO/msjint35.dll | database-library-candidate | 60 | 0 | 60 |
| scripts/DAO/msjter35.dll | database-library-candidate | 84 | 0 | 84 |
| scripts/MCOExOps.asi | patch-or-launcher-investigation | 223 | 0 | 223 |
| scripts/MCOWidescreenMod.asi | patch-or-launcher-investigation | 564 | 0 | 564 |
| softtriz.dll | graphics-library-investigation | 374 | 0 | 365 |
| Stage/.castanet/undo/40/287 | historical-reference | 290 | 0 | 289 |
| Stage/.castanet/undo/40/290 | historical-reference | 23,092 | 0 | 23,038 |
| Uninst.dll | installation-tool | 205 | 0 | 197 |
| voodoo2z.dll | graphics-library-investigation | 120 | 0 | 119 |

The detailed reproducible dependency graph is generated into `build/recovery/`.
Unknown direct destinations remain explicit; indirect and cross-module targets
must be recovered before claiming a complete dependency closure.

Refresh: `python -m tools.recovery_backlog --summary docs/recovery/work-index.md`.
