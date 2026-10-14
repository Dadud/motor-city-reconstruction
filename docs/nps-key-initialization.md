# Login key-record initialization

The verified executable initializes the global request key's trailing 32-bit
field to zero before ordinary login. `prepare_login` and `authenticate` now
use that value by default. Its business meaning remains unknown; zero is an
observed constructor value, not a guessed protocol extension.

Source: `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA/Ghidra 12.1.4 identified the startup table reference at `0x885b20` to
`0x72a6e0`. That initializer calls `0x72a6f0`, which selects wrapper `0xb37e80`
and enters `0x72a700`. The wrapper embeds the key record at offset 4, so its
record address is `0xb37e84`. The constructor clears its 32 material bytes,
16-bit length at record +0x42, and 32-bit value at record +0x44 (`0xb37ec8`).
It also assigns the wrapper/key vtables. This explains why exact references
to the embedded record alone missed initialization.

Original login `0x72a8f0` fills 32 material bytes at `0xb37ea4`, writes length
32 at `0xb37ec6`, and passes the embedded global record to `0x72c3f0`.
That observed branch does not set the trailing value. Serializer `0x71d6d0`
writes a big-endian counted byte string followed by that big-endian value:
`00 20`, 32 private material bytes, then `00 00 00 00`.

Run locally with the external executable and optional Unicorn installed:

```sh
python -m tools.nps_key_initialization_oracle /path/to/mcity.exe
```

On Windows on 2026-10-13, all nine constructor/serializer comparisons matched:
three poisoned initial objects, each serialized at lengths 0, 1 and 32.
The complete wrapper/key-field constructor executes in the original CPU
instructions, including its fixed global target. The base header constructor
`0x7e0670` is replaced by a neutral base object and Windows htons/htonl imports
by exact byte swaps. Supplying material/length replaces the entropy stage.
No RSA, account, network, whole-client startup or live server is executed.

Evidence IDs: constructor `ev_77853260283b590c59e8e554739e9a0bba3fbb1947a22e77b094c03576860cf4`,
global wrapper `ev_b3fa7c9bcad1ad2af51689d3e658f4ae7b17c58a0f4befe4af12582a6fe09790`,
startup reference `ev_30b9aa1b1818a960f82664e89a8e55289329fe6bc37822b78eafe08c21959180`,
serializer `ev_669a98c31d73d1275aca74016465ef85c1af6250998947b948364b34cda016c3`.
Static references can omit indirect writes; this finding establishes startup
and the inspected login path, not every possible process lifetime mutation.
Live fan-server account and race compatibility remains unverified.
