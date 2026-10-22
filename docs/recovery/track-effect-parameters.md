# Track effect parameter normalization

`prepare_track_effect_params` translates native `mcity.exe` function
`0x494dc0`, a direct child of the larger `0x494940` initialization stage.
It operates on a caller-provided block with native offsets preserved because
the full record schema is not known. It updates these fields:

- At `+0xc0d8`, a nonzero signed integer causes `+0xc0dc` to receive the
  float reciprocal.
- Signed integer `+0xc0d0` is clamped down to signed integer `+0xc0c8`.
- Float factors at `+0xc118` and `+0xc11c` become `1.0` when zero or NaN;
  this includes the unordered x87 compare path visible in assembly.
- The signed integer phase at `+0xc134` is multiplied by the binary32
  constant at executable address `0x83c7d4`; the signed integer scale at
  `+0xc130` is multiplied by the binary32 constant at `0x83c7d0`.
- The phase then passes through the binary64 `0x84a198` turn-to-radian factor
  and x87 cosine/sine helpers. The scaled results are stored at `+0xc0e0`
  and `+0xc0e4` as binary32 values.

The complete supplied block is byte-compared with original `0x494dc0`
execution in `tools/track_effect_params_oracle.py`. All 49,464 bytes matched in
512 cases, including zero and negative counts, signed clamp edges, NaN and
infinite factor values, broad phase values, and positive/negative scales.
This verifies the helper over those inputs; it does not reconstruct its parent
initializer or any Direct3D/Windows calls.

Evidence on SHA-pinned `mcity.exe`
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, Ghidra
12.1.4, profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`:

- Function dossier: `ev_ded4ce9793bf0c1ba90c562a99374d9966e2672cef057a9d055b34b05df445a2`
- Instruction sequence: `ev_8dd28d352ff8fb01b3a3981676d721beb6f3e8cefd6ea2ee893b9ec243967652`
- Constants at `0x83b634`: `ev_f7727a20d9ef3250bcb07419b81fcc62b0f6c421ea7277941d3d3efce0687c38`
- Constant at `0x83c7d0`: `ev_faf1097f2e66208438b7771c5b188b9f986e8258e86272af837591b43c1594e4`
- Constant at `0x84a198`: `ev_0c473930b62b17e9e2ae38070ad958e9a3ad5e795d5fdfd39dd2556b77c18847`
- Zero-compare constant at `0x83b638`: `ev_473cdecfc554ad5ce644241844a2e5191d78a787376a3d1596b93e34d544c6d9`
