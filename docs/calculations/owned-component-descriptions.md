# Original outer component descriptions

`apply_owned_descriptions` reconstructs `0x6628d0` in Python and C++.
It writes a NUL-terminated description at offset `0x20` in each 1596-byte record.
The routine works sequentially in input order and preserves bytes after the
new terminator. Its three paths depend on branding and the original special-type
list, rather than ownership alone.

## Template and assembly paths

An unbranded record copies description text from the first matching type-cache
record, searching after the index-zero sentinel. If that template text is empty,
the output becomes a single space. If no matching template exists, the existing
description remains unchanged.

A branded special type creates a list of direct branded children. The parent
index at `0x600` must equal the current record index, and the record itself is
excluded. Child order follows the input array. Each line is:

```text
short model + " " + attachment label + attachment spacer + category
```

Short model is at `0x287`, category at `0x180`, and attachment at `0x61c`.
Attachment zero has an empty label and spacer; any nonzero attachment adds the
spacer. The original label lookup recognizes IDs 1..11, chooses localized text
when available, and otherwise uses its fallback. Unrecognized IDs return an
empty label but still receive the nonzero spacer.

For authored sample values `Model`, `Front`, and `Category`, a nonzero attachment
produces `Model Front Category`. Attachment zero produces `Model Category`;
an unknown nonzero attachment produces `Model  Category`, with two spaces.
The implementation preserves this spacing.

Nonempty existing output receives a newline before the next line. A candidate
longer than 351 bytes is discarded in full and traversal stops, preserving the
previous description. It does not truncate the line or continue to later shorter
children. Three lines of 116 bytes occupy 350 bytes including two newlines.
Lengths 117, 116, 116 occupy exactly 351 bytes and are retained. Three 117-byte
lines would occupy 353 bytes, so only the first two remain.

## Explicit remaining inputs

A branded nonspecial record calls the separate part renderer at `0x668710`.
Its wear-limit logic and table of part-specific callbacks remain unrecovered.
The new interface requires an explicit leaf renderer when this path is reached;
it never silently leaves that path unchanged.

Localized attachment labels are also supplied explicitly. Missing labels for
recognized IDs fail clearly. Unknown IDs preserve the observed empty lookup
result. Caller-provided labels are bounded to 128 bytes without embedded NUL;
this is an authored safeguard, not a recovered localization limit. Model/category
fields require terminators within 64 bytes; template descriptions within 352.

The function can be passed as the description callback to the
[postload sequence](../owned-postload.md), while keeping its leaf/localization
inputs explicit. It is internal reconstruction infrastructure, not the stable
mod interface. Complete descriptions and complete garage loading remain partial.

## Verification

```text
python -m tools.owned_descriptions_oracle /path/to/original/mcity.exe
python -m tools.native_owned_descriptions_compare /path/to/mco_owned_descriptions_compare
```

All 96 cases match the complete original outer function and its real type-cache
lookup and special-type checks. The oracle substitutes branded leaf rendering,
localized attachment lookup and the bounded four-string formatting call. It
compares every output record byte, including retained bytes after terminators.
The same cases match Python/C++ byte-for-byte. Separate tests cover exact 351-byte
acceptance, missing localization, malformed inputs and postload integration.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Outer function evidence:
`ev_7cf1013c317d06cf8417983d5c00118e459ca555866d3269580d5eb81c03115d`.
Attachment lookup `0x66fb40` evidence:
`ev_6497f4904c3abb3778634c2bc5a44eabcb9f0754c615ae6e4a2653602786a93d`.
