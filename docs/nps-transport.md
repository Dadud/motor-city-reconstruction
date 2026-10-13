# NPS TCP connection lifecycle

`client/nps_transport.py` provides explicit socket operations for the recovered
NPS framing. It does not log in or contact a server when imported. `connect`
opens a stream; `send` writes one prepared frame; `receive` returns one `Frame`.
The caller interprets the opcode and body in the appropriate protocol context.
For login, a caller can receive the initial acknowledgement and final response
on the same connection. Persona queries use `query` to open a fresh stream,
send one request, receive one reply, then close it.

The original connection routine `0x72ea50` creates a remote TCP socket and waits
for connection completion, with a 30-second timeout and cancellation callback.
`0x72fd50` passes the complete request bytes to the native send loop.
`0x72f600` waits for a reply, reads four bytes containing big-endian opcode and
total length, then reads exactly the declared remainder. Four-byte frames are
accepted. Request routines choose their wait interval: recovered persona
activation uses 120 seconds. Neither query setup nor frame reception performs
an additional TLS exchange on this binary connection.

The portable implementation preserves the prefix and exact message bytes.
It consumes one frame at a time, leaving subsequent messages on the socket.
It supports partial TCP reads and sends without treating packet boundaries as
message boundaries. Malformed lengths, EOF during a frame, and failed I/O close
the stream. Requests are never automatically retried: reconnecting and replaying
an activation or account operation requires a protocol-level decision.

## Bounds and deliberate improvements

The client rejects outbound frames whose declared length differs from their
actual bytes and rejects incoming lengths below four. The uint16 prefix bounds
each frame at 65535 bytes. Incoming bodies remain hidden in `Frame`'s default
representation. No request, ticket, password, key or response body is logged.

The default connect and send timeouts are 30 seconds, and the default receive
timeout is 120 seconds. A receive deadline covers the entire frame, including
partial body reads; the original routine's explicit wait occurs before reading.
This prevents a peer from holding the client indefinitely after a prefix. These
timeouts are configurable for callers and local tests. Name resolution follows
the operating system resolver; the socket timeout does not guarantee a bound
on DNS resolution. The original callback-driven cancellation and numeric
transport error mapping have not been reproduced by this blocking API.

`query` validates request bytes and timeout values before opening a connection.
Ordinary validation failures on an existing connection do not poison its stream,
because they send no bytes. Once sending or receiving fails, the connection
must be discarded.

## Verification scope

Local socket tests exercise actual byte transfer, fragmented and consecutive
responses, exact outbound bytes, malformed/truncated replies, body timeouts,
and closing the fresh request connection after its reply. They use synthetic
messages and local sockets only. They do not establish authenticated acceptance
by MotorCity Revival, lobby entry, economy or race synchronization.

REA evidence for original receive behavior:
`ev_65be7ce780de4792efa74e5bceeede74cc91966d869c8b65af46bf35a59d1279`.
Original send boundary:
`ev_baa324327952f73f646412290dd605c406709a0f084090f31215173d91665a41`.
Original connection routine:
`ev_c1c27042c767d4f01d8b74a577395c942f73ce662cbecefec6d2b502ec720cda`.
All refer to executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
