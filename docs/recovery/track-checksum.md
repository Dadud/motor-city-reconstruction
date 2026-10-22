# Track loader checksum

`client.crc32.crc32_raw` is the shared arithmetic implementation of native
`mcity.exe` function `0x658280`, used by both the existing NPS executable
identity and the track loader. `track_checksum(data)` exposes it for the FRD
path. The Ghidra pseudocode has an incomplete signature (`void` with one
argument), but its instruction evidence reads the byte count from `[EBP+8]`,
the source pointer from `[EBP+0xc]`, initializes EAX to `0xffffffff`, updates
that accumulator through a 256-entry reflected CRC table at `0x008bdcc8`, and
returns the final EAX value. There is no final complement. The result is
equivalent to `zlib.crc32(data) ^ 0xffffffff`.

The `0x428150` loader obtains the data pointer from `0x6e1720` and a length
through the `0x6e1620` file-size path (whose callback is `0x6e1660`), passes
those values to `0x658280`, and stores the returned word in `0x0097c414`.
`DecodedTrackWorld.loader_checksum` now retains the result for the complete
FRD image supplied to the decoder. The field is preserved as loader metadata;
its later consumers have not been identified.

`tools/track_checksum_oracle.py` compares the translated result with original
`0x658280` execution under Unicorn. Seven deterministic buffers and all 27
installed `Tr.frd` files matched, covering 85,754,464 complete track-file
bytes. This validates the checksum routine and its result over those supplied
buffers; it does not prove full `0x428150` equivalence or native file API
behavior.

Evidence on SHA-pinned `mcity.exe`
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, Ghidra
12.1.4, profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`:

- `0x658280` dossier: `ev_97524b85b651018e3f88bbf578cc26b32eca01425d125a90c1b7922a19d1f32f`
- `0x658280` instructions: `ev_701254f081887d565f531a574d179a3f4d7bc3d19116e665339eb3605e618b02`
- CRC lookup table bytes: `ev_25db498ca7a1e8d8c65babeec0b59e2c04d6c37683657b57b56703b20df688de`
- `0x428150` caller: `ev_8202d7e5585c1226abc8c107ee46dff1257949b71581840b8c556bc69dde6ebb`
- read path `0x6e1720`: `ev_597248840a2e4a0b2943107f24aaf01fe5348cde4edc81ee2d45c161d763f980`
- size wrapper `0x6e1620`: `ev_c2835aa05bc8a9287327f5c12cedff17f705fdc455ce2d08a6ca0fa6643a297f`
- file-size callback `0x6e1660`: `ev_b0c9726f4961557e52179737032aebad48f0244131cde8814b9d6a4cdc8962f5`
