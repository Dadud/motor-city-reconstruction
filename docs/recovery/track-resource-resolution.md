# Track resource variant resolution

`Assets.track_file(track_name, suffix, night, wet)` translates the selection
portion of native `mcity.exe` function `0x4287f0`. Static Ghidra evidence for
the shipped executable shows the resolver trying `Trnw{suffix}` when both
variant globals are nonzero, then `Trn{suffix}` when the night global is
nonzero, then `Trw{suffix}` when the wet global is nonzero, and finally
returning the ordinary `Tr{suffix}` path unconditionally. It checks each
candidate for existence before returning it.

The common path builder is `0x42cc80`; its decompiled format string is
`%s%s\\Tr%s`. The call sites in `0x42cd00` pass resource tails such as
`0.fsh` and `0r.fsh`. Installed tracks contain matching base and night
resources such as `Tr.frd`, `Trn.frd`, `tr0.fsh`, and `trn0.fsh`. The Python
adapter performs case-insensitive lookup using the repository's indexed asset
paths and returns the base path if no candidate exists, matching the native
resolver's unconditional final return.

This translation covers candidate ordering and local existence lookup. It
does not reproduce the native global path roots, flag acquisition, Windows
file API semantics, resource opening, or the rest of the track load sequence.
Static observations are not a full runtime comparison.

Evidence:

- `0x4287f0`: `ev_252b28abf4e229e5cee779ba6ec27749694c1538c45282420473dc0137e49c28`
- `0x42cc80`: `ev_a07b400532dd485cd1a030c4775df1b81beebb775d1c89c3e470cbfbe12c038b`
- `0x42cd00`: `ev_6f7155f05885f9d07e80573b50fb8c92ec89afc62789ed3e3c5f530a2de0fb35`

The target is `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, analyzed
with Ghidra 12.1.4 under profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`.
