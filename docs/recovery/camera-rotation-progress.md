# Camera rotation batch in progress

The free-camera handler at `0x433820` uses three matrix rotations:

| Entry | Operation | Recovered batch axis |
| --- | --- | --- |
| `0x6f1780` | Mix matrix rows 1 and 2 | 0 |
| `0x6f1850` | Mix matrix rows 0 and 2 | 1 |
| `0x6f1910` | Mix matrix rows 0 and 1 | 2 |

The authored implementation is `native/src/camera_matrix_rotation.cpp`. Input angles are turns. Original `0x6f13d0` invokes sine and cosine helpers using the double constant whose value is exactly `6.283185482025146484375`; their results are stored as floats before matrix arithmetic. Multiplications and additions then retain double precision until each float store. Equal source/destination pointers trigger a nine-word copy in the original. The recovered API supports equal or disjoint views and rejects partial overlap; partial-overlap original behavior is not yet recovered.

`tools/camera_matrix_rotation_cases.py` captures all three complete original bodies, including actual trig helpers, with no call substitutions. Synthetic matrices and angles cover identity, signed zeros, nonorthogonal matrices, deterministic random inputs, positive/negative fractional turns, full turns, and endpoints of the declared angle range. The current run captured 4,356 cases; every observed source and result word matched MSVC and Zig output exactly. This finite corpus is regression evidence, not a mathematical proof over every supported value. Host trig behavior outside the tested cases remains a portability concern.

The 4,356 comparisons are now retained in `docs/recovery/corpora/wave0.json` as one multi-root recovery cell. Its manifest and review record cover all three original rotation entries. Generated comparison drivers and focused native tests pass under MSVC and Zig. The aggregate now contains 71 cells and 24,327 routine cases. Checkpoint verification: all 152 MSVC and 154 Zig native tests pass; Python discovery passes 987 tests with seven skips. A fresh hash-checked original execution capture passes all 71 cells and 32 connected traces with MSVC. Zig also passes the complete retained aggregate corpus. Its declared finite input domain excludes nonfinite values, turns outside +/-1024, and matrix magnitudes above 1e20. Floating-point exception flags and original x87 return-register precision are not exposed by this matrix API.

Inventory has been refreshed to 135 explicitly reviewed main-executable entries. Remaining steps: recover native spatial-query dependencies, then connect actual input queries with the free-camera handler. `0x413810` is a no-op in this binary, but the handler's `0x42e760` spatial lookup has real track-data dependencies. That lookup must be recovered or explicitly bounded using original state; it must not be silently replaced with a fabricated success result. Live dispatch and full-game acceptance remain open.

The factory now refuses existing files without a matching generated provenance digest, rather than assuming first-run files are safe to replace. A regression test covers preexisting authored files.
