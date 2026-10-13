# Original missing-component insertion

`client.owned_insertion.insert_owned_placeholders` reconstructs the insertion prefix
of finalization `0x66ea20`. It inserts from resolved type templates rather than
substituting a stock assembly. Entry skip flags, allocation growth, induction pruning
and subsequent assembly passes remain outside this implementation.

## Traversal and eligibility

Inputs are 1596-byte owned slots and a resolved type cache including an abstract-zero
sentinel. The function walks the growing slot list: appended slots can cause later
insertions. A slot is eligible when its abstract ID is nonzero, its type exists in
the cache, and either its PartID at `0x5f8` is nonzero or its abstract type belongs
to the original special-type list. Empty input inserts nothing.

For each eligible parent, cache records whose resolved parent index at `0x600`
equals that parent's first matching cache index are examined in cache order.
Most child types require attachment zero. Types 100001, 110001, 10001, 12001,
11001, 13001 and 14001 require separate attachment 10 and 11 slots. A placeholder
is omitted when any existing slot has the required abstract type and attachment;
this search is global, not scoped to a particular owned parent.

Types 23001, 34001 and 35001 are additionally suppressed when any slot's field
at `0x1e7` equals 2001. This compares that field, not abstract ID at zero.
New placeholders immediately participate in later duplicate/suppression checks.

## Record and display fields

The whole first matching template for the child abstract type is copied. Description
at `0x347` is replaced from the currently examined child template, which can differ
when the cache contains duplicate abstract IDs. Attachment is stored at `0x61c`.

Formatter `0x6623a0` rebuilds display text. Global display mode 2 emits brand, space
and model at `0x207`, including vehicle type 101; it does not apply the owned-part
manufacture-year formatter. Other modes put model at `0x287`; special nonzero types
use model alone at `0x207`, while others use brand plus model. Category at `0x180`
comes from the first matching template. The routine's fifth entry argument is
separate from global display mode at `0xb18014`; entry value 1 skips insertion.

The implementation does not assign a real purchased instance ID. Later passes still
need to establish the complete usable vehicle.

## Verification and safeguards

```text
python -m tools.owned_insertion_oracle /path/to/original/mcity.exe
```

The oracle compares 96 deterministic cases, including every appended record byte
and resulting count, against original instructions `0x66ea54` through `0x66ed71`.
It executes actual cache, eligibility, name and category helpers. Allocation/free
and two bounded `sprintf` formats `%s` and `%s %s` are substituted. Preallocated
slots exclude buffer growth. Host SEH, entry skip flags and the induction tail are
excluded. This verifies the stated prefix under supplied acyclic caches, not all of
`0x66ea20` or live modified-car loading.

The authored function uses a configurable 10,000-part default limit, bounded text
checks, and cache-index/cycle validation. These are portable safeguards, not original
content limits. Owned-slot `0x600` values remain arbitrary signed values because
this pass does not dereference them; the parent pass preserves unmatched values too.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Local REA evidence:

- Finalization: `ev_7c5ef58bf99974e89b70edea0bca13a655b956154accb2c048dd296bbb043745`.
- Child lookup: `ev_5349c320b97c07447c41af834022cc372285bb3a63c12c5fa2324242e9f4d933`.
- Name formatter: `ev_040dcb5e926b4643c4fef840923e26851f83212bf6695224621321c21b7d8b71`.
- Category: `ev_7169d6aa932d6177c8a5ea9e0ef4a53b874a1b3fe53193dacaa417695cd9f4d7`.
