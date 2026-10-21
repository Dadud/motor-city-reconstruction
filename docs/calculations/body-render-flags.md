# Stock body render flags

`client/assembly.py` translates the visual configuration stage of main-client
`0x52e880`. The body model's `:H` groups form an availability mask. Ordered
installed component identities then select roof, mirror, scoop, bumper, fender,
side-board, chin and cage bits. The returned render mask is the intersection
of available and installed flags; mirrors are enabled by default when their
body groups exist, and the firewall bit is enabled when none of the tested
hood/scoop bits is selected.

The ordered class/attachment/filename rule table at PE VA `0x895568` has nine
records. `tools/verify_stock_body_flag_table.py` reads that table and its
pointed-to option arrays from the hash-matched executable and compares every
record, option string and required flag with `CONFIGURATION`. The scoop rule
is order-sensitive: `.factory` is preferred, then large/small scoop and hood
hole combinations in the original order. A blower forces the scoop filename
to `.hole`; unsupported scoop filenames also fall back to `.hole`.

The owner-node name mutation rules are represented by
`normalize_body_component_names`: the first `1001` node is renamed `SUSP`; the
first `40001` scoop node is renamed `.hole` when a named `340333` blower exists,
or when a `350001` scoop exists and the name is outside `.factory`, `.large`,
and `.small`. The helper preserves list order and returns copied nodes. It is
not yet wired into complete owner-list production or the preview render graph.
`tools/verify_body_component_names.py` executes eight synthetic bodyless owner
lists through original entry `0x52e880` and compares complete node bytes,
mutations and the fallback flag. This isolates the name side effects from body
render-list allocation. `tools/verify_stock_body_flags.py` also executes the
full body-group scan and compares output flags, owner/node bytes and mutations
for 14 synthetic model/component lists. It includes the original `0x52db70`
collector in every body-model case. `tools/verify_stock_body_catalogue.py`
extends this comparison to 204 of the 212 catalogued stock vehicles available
in the installed asset set. It decodes each installed body FCE, constructs the
direct linked-node layout consumed by `0x52e880`, and compares flags,
component-name rewrites, and complete owner/node write boundaries. Seven
vehicles cannot be compared because their VIV archives are absent; one
catalogue vehicle has no unique body definition. This verifies the body-mask
stage with real stock assets and catalogue identities, but does not prove that
the game's earlier owner-list producer builds these same nodes or that the full
preview graph matches. `ConfigDefault` is not used as a substitute for the
original flag test.

Run the static table check with:

```powershell
python tools/verify_stock_body_flag_table.py "<installed game>\mcity.exe"
python tools/verify_body_component_names.py "<installed game>\mcity.exe"
python tools/verify_stock_body_flags.py "<installed game>\mcity.exe"
python tools/verify_stock_body_catalogue.py "<installed game>\mcity.exe" "<installed game>"
python -m unittest tests.test_assembly
```

The table check proves the literal option table for this executable hash. The
catalogue check reports its exact compared and unavailable vehicles; its
constructed owner list does not verify the game's owner-list producer or
complete preview equivalence.

REA Evidence: function dossier
`ev_fdc3599d736c213996d6327b0860e4da38c46bcd6e481065814f4f36969cbe54`,
option-table bytes
`ev_c63bf526f159bf3c1c4e72bde08fe47528a30a01c26c6d1de82806d8c62d94a8`,
and static alias bytes
`ev_e5203be417894957fef8527d3351c9c0b8eb9f7a39b29350f6a9eab804a35a41`.
