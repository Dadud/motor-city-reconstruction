# Mouse driver setup and callable labels

Setup `0x6f06c0..0x6f0711` is a complete Ghidra function body of 82 bytes, recorded by REA Evidence `ev_56f5f64355be7be4e18a42f1ff5989f4b65643f0f36a21b27dd0a6c61aba4f27`. It copies current width/height to maximum bounds, zeros minimum bounds and counter `0xb36590`, enables mouse handling, and installs decrement/increment/report identities `0x6f06b0/0x6f06a0/0x6f0670` at `0x8c4708/0c/10`. It preserves the cached coordinates, buttons and button callback.

Five registered callable labels are absent from the retained Ghidra function enumeration. `analyze_function` explicitly rejected those selectors. Exact-address REA instruction walks instead followed all in-range branch successors to returns. Together with initializer/setup registration references and complete original calls, these establish the explicit supplements below. They are not claims of FunctionManager ownership or changes to the original enumeration.

| Entry | End exclusive | Observed behavior | Entry instruction Evidence |
| --- | --- | --- | --- |
| `0x6efa60` | `0x6efa90` | Gate on nonzero owner/enable and matching target window; add signed high word of wParam to wheel accumulator `0xb36238`; return zero; RET consumes 24 argument bytes | `ev_e150faf729d98e3e3e3a8a1d12f8d879df038b38cd8a9d31ea94cfddbd28b59e` |
| `0x6efad0` | `0x6efae2` | Execute recovered cleanup, then clear lifetime initialization and mouse enabled | `ev_0d2b2bbe73297bb35ae689f599bc25dc997982e660bae66f1597d195ae2360da` |
| `0x6f0670` | `0x6f0698` | Copy cached X/Y/buttons to `0x8c4600/04/08`; return buttons | `ev_f6e4cfaa38a61b058a864780f030d954fed117276966deee998da8d9f964a24a` |
| `0x6f06a0` | `0x6f06a7` | Increment counter modulo 2^32 | `ev_231f3cf22d16c995cc7e36ade0954e3e453ec68ce3fbb38979714aab94447ac8` |
| `0x6f06b0` | `0x6f06b7` | Decrement counter modulo 2^32 | `ev_5080f72fbf7eb464510cbd0108fe1651171bf9bbcf0eb770dd0c95017dd42a39` |

All reachable instruction records are private in `evidence/rea-mouse-batch-final.bundle.json`; terminal and intermediate records retain the same pinned target/provider/profile as [the setter](mouse-state-progress.md). `function-supplements.json` distinguishes these five callable entries from the base enumeration. No bytes or pseudocode are published.

576 complete original calls compare setup, signed wheel deltas, addition/counter wrap, enable/window rejection, reporting and shutdown with actual cleanup and mutable opaque handles/tables. Independent native checks enforce representative wrap, gating, setup identities, report values and persistent cleanup-registration flag. Void operations do not expose incidental original register values as return contracts. Runtime tests additionally exercise real message registration/dispatch and the cleanup registry; see [the batch checkpoint](mouse-batch-progress.md).
