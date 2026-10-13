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
