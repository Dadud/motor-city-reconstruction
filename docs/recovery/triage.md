# Function triage

Rule-based classification of every exported function, then published
dispositions decide what counts as required work. `no-direct-callers`
is a review signal rather than a deadness finding.

| Binary | Role | Entries | Required | Distinct shapes |
| --- | --- | ---: | ---: | ---: |
| mcity.exe | game-client | 25,779 | 11,760 | 6,569 |
| nps/mco.exe | online-support-investigation | 2,985 | 2,708 | 0 |
| ip.exe | online-support-investigation | 2,377 | 1,711 | 0 |
| IFC22.dll | input-library-investigation | 899 | 792 | 0 |
| nps/mrbupd.dll | online-support-investigation | 589 | 444 | 0 |
| nps/authlogin.dll | online-support-investigation | 496 | 384 | 0 |
| scripts/MCOWidescreenMod.asi | patch-or-launcher-investigation | 564 | 0 | 0 |
| nps/NPSAnlyz.dll | online-support-investigation | 54 | 0 | 0 |
| softtriz.dll | graphics-library-investigation | 374 | 0 | 0 |
| dx7z.dll | graphics-library-investigation | 186 | 0 | 0 |
| mco-launcher.exe | patch-or-launcher-investigation | 4,348 | 0 | 0 |
| scripts/DAO/msjint35.dll | database-library-candidate | 60 | 0 | 0 |
| voodoo2z.dll | graphics-library-investigation | 120 | 0 | 0 |
| scripts/DAO/msjter35.dll | database-library-candidate | 84 | 0 | 0 |
| IMPLODE.DLL | compression-library-investigation | 67 | 0 | 0 |
| Compress.dll | compression-library-investigation | 14 | 0 | 0 |
| Stage/.castanet/undo/40/290 | historical-reference | 23,092 | 0 | 0 |
| nps/PBA.exe | online-support-investigation | 178 | 0 | 0 |
| Stage/.castanet/undo/40/287 | historical-reference | 290 | 0 | 0 |
| nps/ProxyTool.exe | online-support-investigation | 186 | 0 | 0 |
| scripts/DAO/msjet35.dll | database-library-candidate | 3,693 | 0 | 0 |
| scripts/MCOExOps.asi | patch-or-launcher-investigation | 223 | 0 | 0 |
| scripts/DAO/dao350.dll | database-library-candidate | 1,571 | 0 | 0 |
| 3dSetup/3DSetup.exe | installation-tool | 2,885 | 0 | 0 |
| Uninst.dll | installation-tool | 205 | 0 | 0 |
| dinput8.dll | patch-or-launcher-investigation | 6,539 | 0 | 0 |
| 3dSetup/3DSetup.dll | installation-tool | 1,365 | 0 | 0 |
| dx8z.dll | graphics-library-investigation | 300 | 0 | 0 |

| Class | Entries |
| --- | ---: |
| game-candidate | 64,588 |
| linker-artifact | 9,092 |
| import | 3,817 |
| crt-runtime | 848 |
| thunk | 827 |
| eh-artifact | 324 |
| tool-artifact | 27 |

Review signal — `game-candidate` entries with no direct caller: **9,549**. Indirect dispatch is not recorded by this pass, so this is a work queue, not dead code.

## Required set

- Required entries after dispositions: **17,799**
- Distinct code shapes behind them (lower bound on behaviors): **6,569**
- Entries still awaiting a disposition: **0**
- Of which in modules whose internals have not had region treatment: **6,039** (their module role is reviewed, their contents are not)

An entry counts as required when its module is in recovery scope and no
published disposition removes it. Dispositions live in
`docs/recovery/dispositions.json` with the evidence for each decision.

Distinct code shapes are measured only for modules whose original binary
was supplied to this run, so the shape total understates the full set.

## Wave order (region-level first cut)

Wave execution: W0 67/658, W1 0/1,189, W2 0/437, W4 6/1,078, W5 16/6,635, W6 3/1,763
92 of 11,760 required entries covered across 4 active wave(s).

| Wave | Required entries |
| --- | ---: |
| W0 | 658 |
| W1 | 1,189 |
| W2 | 437 |
| W4 | 1,078 |
| W5 | 6,635 |
| W6 | 1,763 |

## Address-region work queue: mcity.exe

Game logic and bundled libraries share address space and carry no
symbols, so the rules above cannot separate them. Regions are the
review unit: each needs an owner decision before the required count
is real. Known-good reviewed functions all fall in 0x430000-0x550000.

### mcity.exe

| Region | Required entries | Distinct shapes | Ratio | Note |
| --- | ---: | ---: | ---: | --- |
| `0x400000` | 658 | 507 | 1.3x |  |
| `0x440000` | 855 | 627 | 1.4x |  |
| `0x480000` | 908 | 590 | 1.5x |  |
| `0x4c0000` | 197 | 107 | 1.8x |  |
| `0x500000` | 437 | 328 | 1.3x |  |
| `0x540000` | 662 | 478 | 1.4x |  |
| `0x580000` | 804 | 549 | 1.5x |  |
| `0x5c0000` | 767 | 502 | 1.5x |  |
| `0x600000` | 896 | 533 | 1.7x |  |
| `0x640000` | 1,189 | 814 | 1.5x |  |
| `0x740000` | 1,301 | 911 | 1.4x |  |
| `0x780000` | 1,078 | 764 | 1.4x |  |
| `0x800000` | 2,008 | 166 | 12.1x | inventory density anomaly: review before counting |

Refresh: `python -m tools.function_triage`. Rules live in this module and
are deliberately explicit so a contested classification is a one-line
change with a recorded consequence.
