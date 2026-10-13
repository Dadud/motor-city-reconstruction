# Original owned-component ordering

`client.owned_ordering` reconstructs recursive ordering procedure `0x66f0d0`
and the count-equality acceptance rule in caller `0x66f2b0`. The traversal uses
the resolved abstract-type cache, not owned parent links or attachment geometry.
It produces a candidate sequence; that sequence need not be a permutation.

## Traversal and matching

Traversal begins with the abstract type of the first input slot. At each visit,
it checks attachments in original table `0x8c007c` order:

```text
10, 1, 2, 5, 11, 3, 4, 6, 7, 8, 9, 0
```

Table value 12 terminates the scan and is not a supported attachment. For each
attachment, the first original input slot matching both abstract ID and attachment
is copied in full. Input records are never consumed. Further records sharing that
pair are ignored, while a later visit to the same type can copy the first record
again. Unsupported attachments are omitted.

After scanning a type's attachments, traversal visits its cache children depth-first
in cache order. A child is a cache record whose resolved parent index at `0x600`
equals the first matching cache index of the current abstract type. Abstract zero
and missing types have no children. Duplicate abstract IDs in the cache can therefore
cause repeated visits and repeated copies of the same input record.

## Worked examples and the acceptance trap

Suppose the first slot has type 101. The cache lists child 1001 under 101 and
child 2001 under 1001. Input slots appear as:

```text
A: type 101, attachment 0
B: type 2001, attachment 0
C: type 1001, attachment 11
D: type 1001, attachment 10
```

The candidate sequence is **A, D, C, B**: type 101 first, then type 1001's attachment
10 before 11, then its child 2001. It does not follow input order or owned parents.

Now let a cache list child type 1001 twice under 101. Inputs are A (101/0),
B (1001/0), and C (1001/0), with B first. Candidates become **A, B, B**. The caller
accepts this sequence because its count equals the three input slots, even though
C disappears and B is repeated. Do not replace this count-only rule with a uniqueness
or permutation test while claiming original behavior.

`reorder_owned_parts` returns the candidates only when their count equals the input
count; otherwise it returns the original sequence unchanged. This caller rule is
derived from static original evidence, not execution of the database loader.

## Verification boundary and safeguards

```text
python -m tools.owned_ordering_oracle /path/to/original/mcity.exe
```

The deterministic 96-case corpus passes, comparing whole-record output and count
with original recursive ordering and real cache/initialization helpers. Allocation
and free are substituted; FS:[0] exception-chain storage is isolated inside the
emulator. Empty input is checked only at the authored API because no first input
abstract type exists. The corpus total includes those API-only empty cases.
The full database loader and its acceptance branch are not executed by this oracle.

The authored implementation validates cache indexes/cycles, limits input and output
to 10,000 parts by default, and caps type visits at 100,000 even when repeated cache
paths produce no output. These are safety bounds, not recovered game limits. The
same bounds apply to the portable native implementation. None of these passes by
itself establishes complete assembly, simulation inputs or online compatibility.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Local REA evidence:
`ev_44eec0af6117c9c554f9f363a7bfc18a6d1d982b146285bcb0a09c4333bb05c5`.
