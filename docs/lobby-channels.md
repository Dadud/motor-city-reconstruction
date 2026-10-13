# Server connections and room channels

The original lobby interface separates connecting to a server from adding a
room channel. This matters when integrating login: the room operation cannot
replace server authentication.

The singleton factory at `0x730450` installs interface table `0x84b3fc`.
Its entry at offset 4 points to server connection routine `0x73a720`, while
offset 8 points to channel-add routine `0x738f00`. Game room operation
`0x44eba0` calls offset 8 with a room argument structure and two callbacks.
The factory is retained by game network objects constructed at `0x44cce0`,
`0x44fb20`, and `0x456170`.

Channel-add first accepts only protocol values `0x21`, `0x2c`, `0x37`, and
`0x42`. It looks up the server connection through the connection registry.
When no connection exists, it returns -6 and reports "Server Not Connected".
It rejects an already-open nonzero channel ID with -5. A zero requested channel
ID is permitted; the server supplies the result later.

The channel object receives its user ID from the existing server connection
field at offset `0x108`. The caller's two callback values are stored separately
in channel fields `0x2c` and `0x30`.

For protocols `0x2c` and `0x37`, the routine uses a UDP socket. It reuses an
existing connection UDP socket when available. Otherwise it creates one on the
requested local port or asks for an available port when the request is zero.
A requested nonzero port that disagrees with an existing UDP port fails with
native return -59. Socket creation failure returns -31.

For `0x21` and `0x42`, the routine reuses the existing TCP socket. A differing
requested port is ignored and the room argument is updated to the existing
connection TCP port. This observed distinction does not yet establish the
application names or reliability semantics of all four protocol values.

These are static findings from executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`:

- Interface factory: `ev_655514d5c4aa166835a717ecaf6769d9b84bb3a3d0fe07fe0e7cb1d415b42514`.
- Game room operation: `ev_9396f7061e55ec9fd8261fc8f0aab217bc1b1439bccef1fedda954247dea9b2c`.
- Channel-add routine: `ev_3e3ea38f01df2e4f9827438f500cb911b3e218d2d2a1db4376e910dd0d57da94`.

The remainder of channel negotiation, initial server-argument construction,
the 64-byte login field's upstream source, and actual authenticated room joining
remain unresolved. No room request was sent during this investigation.
