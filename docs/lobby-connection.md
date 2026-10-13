# Login key retention and lobby connection setup

The original client preserves its own generated session material after binary
login succeeds. In `0x72a8f0`, it allocates a separate key-record object, copies
the generated global key into it, then returns that object's pointer at result
offset `0x2c`, its length at `0x28`, and its bytes at offset `8`. The record read
from the `0x601` response is a separate object. Replacing the retained request
key with that response record would change this observed behavior.

Connection constructor `0x73f050` accepts a key-record pointer through argument
structure offset `0xc4`, copies at most 32 bytes into its own record, and calls
crypto setup `0x73f470`. That setup uses the first eight bytes with independent
send/receive DES-CBC chains and zero initial IVs. `LobbyCiphers.from_login`
constructs those TCP contexts from `PreparedLogin.session_material`. UDP chains
and transport activation remain separate. A new instance creates fresh chains;
the precise reconnect policy still requires recovery.

Before building the connection login, `0x73a720` calls `0x73c8c0`. If argument
byte `0xd0` is zero, this queue step returns immediately. Otherwise it waits for
queue messages. ID `0x231` updates two uint16 queue-status outputs; `0x21e`
reports a version mismatch and fails. ID `0x230` allows login to proceed.
The exact compressed payload formats and which game caller enables this queue
remain unresolved; no guessed queue parser or lobby login has been sent.

Static evidence for executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`:

- Login retention: `ev_9cc09802927e8977bdbc4dcf5fc81fb8fd7e84e6453b91e751b28d4e53ee4cc8`.
- Constructor: `ev_5f77f350622e932f77666a39da638eb8367953941a1e0a9dfc2772e80f92690c`.
- Connection procedure: `ev_39df527653aa4915699923f6f95d53e9aef1c2f0028e934df189e431e99c737e`.
- Queue step: `ev_2909f87cde734b140052fa69fc0dbc3a922b2763d8a29353f068ba418d6083c7`.

Tests exercise independent directions and connections, first-eight-byte key
selection, and rejection of decoded server records as client request keys.
They are synthetic checks; authenticated fan-server compatibility is unverified.

## Connection login packet

The connection procedure selects ID `0x100`, or `0x301` when its caller value
at offset `0x68` equals signed `-0x2002`. Builder `0x7e5e60` uses the same
payload packer for both. It sends this packet directly, before constructing the
normal connection cipher contexts. Its framing is the four-byte prefix.

Despite the native name "Compress", this path packs fields without a general
compression algorithm. Packer `0x7e47d0` uses format strings `lpb` then `llpppb`.
The common writer `0x7e4140` writes `l` as a big-endian uint32, `p` as a
big-endian uint32 byte count followed by bytes, and `b` as fixed bytes.

| Order | Native input offset | Encoding | Observed use |
| --- | --- | --- | --- |
| 1 | 0 | uint32 | User ID |
| 2 | 4 | Count plus NUL-terminated string | Username, buffer 32 |
| 3 | 0x24 | 64 fixed bytes | Key-derived blob; derivation still under investigation |
| 4 | 100 | uint32 | Caller-supplied value |
| 5 | 200 | uint32 | Caller-supplied value |
| 6 | 0xcc | Count plus NUL-terminated string | Version, buffer 32; caller supplies `4.5.0.0` |
| 7 | 0x78 | Count plus NUL-terminated string | Hostname, buffer 64 |
| 8 | 0xb8 | Count plus NUL-terminated string | IP text, buffer 16 |
| 9 | 0x68 | 16 fixed bytes | Meaning unresolved |

Counts include each string's terminating NUL. This differs from the binary
authentication packet's uint16 strings, whose counts exclude NUL. The native
size helper `0x7e4920` supplies a fixed payload capacity of 255 bytes.
`client/lobby_login.py` encodes these fields with explicit unknown inputs.

Three synthetic cases, including empty strings, uint32 extremes, binary fields,
and maximum string-buffer lengths, matched the actual `0x7e47d0` instructions
under bounded Unicorn emulation. Run `python -m tools.lobby_login_oracle`
with the verified original executable path. This verifies the payload packing,
not the key-blob derivation, connection acceptance, or gameplay.

Additional static evidence:

- Builder: `ev_eee230575b54d5dc1533f9be2eae357f55d6658186de3a5bd1aac9be14ac34ac`.
- Packer: `ev_393669a47a2677681e455eda97680b5e7f1eb0012af8eeeac33f97220d0d4217`.
- Size helper: `ev_7a4de83cdff63f3b4257a37604a7c579ecf6ef476cdee87302d2d635bfb5d389`.
- Field writer: `ev_0d2b2ddfa965f2ae67729e2d4005e1d05586002fadd7fd7770fa6535cc5abce2`.
