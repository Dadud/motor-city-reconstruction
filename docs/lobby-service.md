# Portable lobby connection service

`client/lobby_connection.py` connects the recovered login, queue and cipher
components. `connect_lobby(endpoint, login, prepared_login)` opens a TCP stream,
waits for login permission, sends the supplied login packet, requires a valid
success reply, and returns an owned `LobbyConnection`. Importing it performs
no network I/O. Persona activation remains a separate preceding operation.

The original connection routine `0x73a720` calls queue helper `0x73c8c0` before
building the connection login. With the game's queue flag enabled, that helper
waits for `0x230` permission. `0x231` carries two big-endian uint16 values using
packing format `ss`; the helper reports the user's position and queue total.
`0x21e` is version mismatch and returns -34. The portable callback receives
`LobbyQueuePosition` when a queue update arrives.

The login packet `0x100` is sent directly to the socket. The original routine
parses plaintext success `0x120` or `0x308`, updates its persona ID, then creates
the connection object through `0x73f050`. That constructor copies the retained
client key and initializes its cipher contexts through `0x73f470`. Encrypting
the initial login packet would reverse this ordering and produce incompatible
bytes. The portable handshake therefore uses no cipher for queue or login.

After success, `LobbyConnection.send` wraps ordinary messages in encrypted
`0x1101` envelopes. It excludes heartbeat opcodes `0x207` and `0x217`, matching
the native selector. The caller supplies the final partial-block padding
explicitly; it is not PKCS padding. The original sender's scratch tail is opaque
and is not reproduced by retaining stale memory. `receive` decrypts wrapped
messages while preserving its CBC chain and returns their inner frames. Plain
frames, including heartbeat frames, remain visible through the raw `receive` API.
`receive_message` follows the native receiver: it consumes 0x207 and answers
0x217 with an empty plaintext 0x207 before returning an application message.
It handles plaintext or decrypted heartbeat opcodes without changing the
outbound CBC chain. The original builder's null-payload branch emits exactly
four bytes for this reply, not an NPS 12-byte header.

Use a context manager or `close()` when finished. Closing is idempotent and ends
both cipher contexts. Socket failures, invalid encrypted frames and malformed
handshake success replies close the stream; failed account messages are not
retried. A new connection creates fresh zero-IV chains from the retained request
material rather than reusing a prior connection's state. Each frame is limited
to the original lobby receiver's 60000-byte maximum.

## Limits and deliberate differences

The default queue phase has a configurable 120-second total deadline. The native
code repeats 30-second waits and supports a cancellation callback. The portable
service also bounds the login reply phase at 30 seconds. Unknown queue messages
fail explicitly instead of reproducing the native helper's prefix-only discard;
permission frames with unexpected bodies are rejected. These choices prevent a
malformed reply from leaving the stream misaligned. They have not been tested
against the live server's queue behavior.

This service does not dispatch rooms or game channels, schedule unsolicited
keepalives, bind MCOTS, reconnect, or synchronize a race.
The returned success identifies the accepted persona but does not prove a fully
working multiplayer session. Authenticated fan-server lobby entry remains
unverified.

Tests check queue ordering, plaintext login, rejection cleanup and bounded
success decoding. Real local socket tests exchange consecutive encrypted
messages in both directions, preserve chaining around a plaintext heartbeat,
and discard a stream after a malformed envelope. Fixtures use synthetic keys
and no external account.
An additional loopback peer exercises the complete queue-to-plaintext-login
exchange, followed by an encrypted application message and the automatic
heartbeat reply. This validates actual socket integration rather than only
mocked handshake calls. It does not emulate the full fan server.

REA evidence:

- Connection sequence: `ev_36222cf2f2588a960d68a8d6c80b59748a3b97e5acba0bcc00fb80d18c9324b9`.
- Queue helper: `ev_2909f87cde734b140052fa69fc0dbc3a922b2763d8a29353f068ba418d6083c7`.
- Queue payload reader: `ev_893e71fc6b21523217e3cd52e187d9dd3c475554e6b86671aefc59f2d3c804a6`.
- Connection constructor: `ev_6b4209d36a438b80c2b6a38581f92c53d481abc97aa75fd32912c2fe04ae764a`.
- Heartbeat receiver: `ev_59786f1f74c6865b10f573fd70616a5690b7837f20a2c878229420ed944bc46b`.
- Reply builder: `ev_eee230575b54d5dc1533f9be2eae357f55d6658186de3a5bd1aac9be14ac34ac`.

All refer to executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
