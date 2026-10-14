# Native plain NPS framing

`native/include/mco/nps_framing.hpp` ports the evidence-backed Python
`client/nps_framing.py` codec to C++20. It supplies byte framing for a future
native service client. It performs no network I/O, encryption, authentication,
retry, or payload construction beyond the generic optional header.

## Evidence and layout

The original main executable SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Serializer `0x7e0800` and receiver `0x72f600` establish the plain envelope
described in [networking.md](networking.md#recovered-binary-framing).
The receive evidence is
`ev_65be7ce780de4792efa74e5bceeede74cc91966d869c8b65af46bf35a59d1279`.
The source and tests here are authored implementations, not decompiler output.

Every frame starts with big-endian uint16 message ID and total byte length.
The total includes this four-byte prefix and ranges from 4 through 65535.
Unknown IDs and body bytes survive decoding unchanged. A four-byte frame is
accepted; its purpose remains unresolved.

The header-enabled serializer adds these body fields:

| Wire offset | Type | Value |
| --- | --- | --- |
| 4 | uint16 big endian | `0x0101` for IDs `0x501..0x51a` or `0x521..0x526`; otherwise zero |
| 6 | uint16 big endian | Zero |
| 8 | uint32 big endian | Explicit caller-supplied auxiliary value |
| 12 | bytes | Message-specific payload |

Auxiliary interpretation depends on the original message object and remains
outside this generic codec. A default of zero is an API default, not evidence
that a service accepts zero for a particular operation. The explicit header
reader preserves received flags and reserved values, even if the serializer
would choose different values. It rejects bodies shorter than eight bytes.

## API and failure behavior

`encode_nps_frame` serializes a `NpsFrame`; `encode_nps_message` emits the
header-enabled form. IDs and auxiliary values use fixed-width C++ unsigned
types. Callers parsing wider or signed external values must validate before
narrowing them. Oversize bodies throw `std::invalid_argument` before copying.

`NpsFrameDecoder::feed` accepts fragmented or coalesced stream bytes and returns
complete frames. Only one incomplete frame is buffered, bounded by the uint16
length. Lengths below four permanently fail the decoder, including subsequent
empty feeds. `finish` checks EOF and rejects a failed decoder or partial prefix
or body. Discard the connection after these failures. These failure rules match
the Python reconstruction's defensive framing policy.

## Verification

The native unit test checks all 65536 IDs against the documented flag ranges,
every split of a mixed short-frame stream, a maximum frame delivered one byte
at a time, invalid lengths and terminal decoder failure, each truncated position
of a message, size boundaries, and preservation of opaque header fields.

The private comparison runner consumes synthetic bytes on standard input. Its
mode arguments are test harness operations, not game opcodes. Run after building:

```text
python -m tools.native_nps_framing_compare build/native-check/mco_nps_framing_compare.exe
```

Local Windows verification using Zig C++20 passed the standalone unit test and
matched Python in 108 serializations, 21 fragmented/coalesced stream decodes,
12 header decodes, and 66 rejected cases. The corpus includes maximum lengths,
flag boundaries, opaque bytes, oversize payloads, malformed lengths, and EOF
truncation. `original_binary_executed` and `live_server_tested` are both false:
this port reuses existing original evidence and compares against the Python
codec. It adds no fresh runtime evidence from the original executable or
authenticated server sessions. Linux builds and native socket integration
remain separate acceptance work.
