# Original induction placeholder pruning

This is the final pruning phase of component finalization `0x66ea20`, executed
at `0x66ed71..0x66f0ba`. It follows earlier missing-part insertion. The authored
Python and C++ functions implement this isolated phase, not the entire finalizer
or its entry-point enable/skip conditions.

The installed catalogue identifies two ordered groups:

| Group | A | B | Placeholder |
| --- | --- | --- | --- |
| Air intake | 340001 Air Cleaner | 340333 Air Scoop | 340666 Air Intake Point |
| Boost | 350001 Blower | 360001 Nitrous Injector | 350666 Supercharger |

For each group, the original scans all current records to determine whether any
A or B record has a nonzero owned PartID at `0x5f8`. It then follows these rules:

| Ownership found | Removal sequence |
| --- | --- |
| Neither A nor B | First A, then first B; placeholder remains |
| A only | First B, then first placeholder |
| B only | First A, then first placeholder |
| Both A and B | First placeholder only |

These are record-selection rules; they do not establish mechanical compatibility
or the effect of blower/nitrous on engine calculations. Placeholder ownership
is not tested in this phase. Only the first record of each removal type is removed;
duplicates are not collapsed. Each removal copies the last entire 1596-byte record
into the removed position and reduces the count. Remaining array order therefore
changes. The boost group sees the air-intake group's already modified array.

No retained record fields are edited. Root selection and parent/dependency linking
must happen after the original finalization order has been respected. This phase
alone cannot supply a finalized vehicle.

## Verification

The CPU oracle executes the original pruning instructions without host imports,
allocation, missing-part insertion or SEH restoration. All 97 synthetic cases
match retained record bytes, logical counts and successful return values. The
asset-free native/Python comparator uses the same corpus, including all ownership
combinations, duplicate types, ordering changes and empty input.

```text
python -m tools.owned_induction_oracle /path/to/original/mcity.exe
python -m tools.native_owned_induction_compare build/native/mco_owned_induction_compare
```

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Static full-finalizer evidence:
`ev_7c5ef58bf99974e89b70edea0bca13a655b956154accb2c048dd296bbb043745`.
The earlier insertion rules and finalizer call arguments remain separate recovery
work. No original client session or complete owned-car startup is claimed here.
