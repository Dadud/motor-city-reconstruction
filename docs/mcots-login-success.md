# MCOTS login-success payload

Login operation 0x69 receives a richer operation 0xd5 success record. Both
operations map to completion handler `0x682590`. That handler recognizes 0xd5,
copies scalar fields to client globals, forces its success argument to 1,
then correlates the pending transaction and processes services. This order
does not make an unsolicited 0xd5 a valid login: the native pending lookup can
still fail and close connections.

`client.mcots_login_response.MCOTSLoginSuccess.from_frame` requires a matching
pending transaction before it parses a plaintext payload. The record's
minimum observed size is 173 bytes, because the handler reads a four-byte
field at +0xa9. The parser retains extensions and unresolved bytes without
assigning meanings. It does not establish service connections.

| Payload offset | Bytes | Observed use |
| --- | --- | --- |
| 0 | 2 | Operation 0xd5 |
| 2 | 4 | Value stored at global 0xb2a098 on the positive branch |
| 6 | 1 | Feature flags; bits 0, 1 and 2 copied to separate globals |
| 7 | 2 | Unresolved, preserved |
| 9 | 24 | Six little-endian values, exposed as `values_09` |
| 0x21 | 104 | Four 26-byte service records |
| 0x89 | 36 | Nine little-endian values, exposed as `values_89` |
| 0xad | remaining | Extension, preserved |

The first four bytes of each service record are a service ID. The handler
skips ID 0xff and advances exactly 26 bytes for each of the four slots. The
remaining 22 bytes are opaque in the current reconstruction. The inspected
slot-selection loop writes a local slot index and does not itself copy an
address or port from the record. Their configuration path needs further
tracing; no automatic connection should guess its fields from their size.

Scalar destinations, in payload order:

- `values_09`: 0xb29a50, 0xb29a54, 0xb29f84, 0xb29f78, 0xb29f60, 0xb29f80.
- `values_89`: 0xb29f64, 0xb29a58, 0xb29a5c, 0xb29a60, 0xb29a64,
  0xb29f68, 0xb29f6c, 0xb29f70, 0xb29f74.

Names such as currency, time or permissions are not yet assigned to these
values. Feature bits also retain their original numeric positions until
their consumers establish a meaning.

`python -m tools.mcots_login_response_oracle /path/to/original/mcity.exe`
executes the original handler from `0x682590` to `0x682679`, stopping before
pending lookup. Three patterned payloads, with flag bytes 0, 5 and 255, matched
all fifteen scalar destinations and three feature globals. This checks
unaligned offsets and flag extraction. The bounded oracle does not execute
the later value-at-+2 store, service selection, service attachment or network
I/O; those are static observations rather than runtime verification.

The current parser is one part of login reconstruction. A successful live
login still requires attachment, encryption, transaction transport and the
service follow-up behavior to be integrated and verified against the fan
server.

Evidence: `ev_42b9b05a5ddaf57e495d100245468a26374f6a5685a855ee46fa0bd9e6986d3f`.
Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
