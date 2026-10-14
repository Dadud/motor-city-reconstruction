# Native channel image construction

`native/include/mco/lobby_channel_record.hpp` ports the bounded Python
`client/lobby_channel_record.py` data writes into C++20. This is a private
reconstruction boundary for the original `0x15c` argument and `0x3bc` object
layout. Neither layout is a stable mod API.

## Required inputs and preserved bytes

`initialize_channel_image(argument, allocated_image)` requires exact-size
spans and returns a `ChannelImage`. The supplied allocation image is mandatory.
The function never assumes the allocator zeroed memory. It reproduces the data
defaults and constructor field writes described in
[lobby-channel-record.md](lobby-channel-record.md), leaving all other bytes
unchanged. Host vtable installation and critical-section initialization are
excluded; host addresses are neither installed nor invoked.

Name copying matches `strncpy(...,30)`: a NUL pads the remainder of those thirty
bytes, while object bytes `0x2a..0x2b` always retain allocation contents. A name
with no NUL in its first thirty bytes is copied unchanged. The function does not
append a terminator in those two untouched bytes.

Flags produce the original short bit patterns: object `0x6e` receives 1 when bit
0 is set, otherwise 4 when bit 2 is set, otherwise 2; object `0x6a` receives
`flags & 0x20`; object `0x82` receives `flags & 0x4000`. Complete flags survive at
object `0x190`. Other argument fields retain their original bytes without
interpreting their meaning.

`materialize_channel_record(image)` requires a complete object image with any
connection and caller overrides already supplied. It returns a `ChannelRecord`
of exactly `0x1a4` bytes, suitable for the separate recovered payload serializer.
It copies mapped object fields into the record and preserves unmapped record
bytes from the input. Original metadata copied to object `0x346` lies outside
this record and is not exposed by this return value.

Neither function validates a string as a wire string, supplies user IDs, chooses
a transport or server, initializes sockets, or sends requests. A record with
allocation-derived nonterminated strings can still fail the bounded payload
serializer; constructing an image does not prove it is valid to send.

## Evidence and verification

The original executable SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Existing original comparisons cover 36 constructor cases and 36 record-copy
cases. Constructor `0x743d50` evidence is
`ev_14df97a517e0986b98f1ce863f52406f38e8f32be825efe40491c66ad8cf330b`;
defaults `0x7440c0` evidence is
`ev_e6aa9342bf7da0d33a8bca8bc680777d1e65b545c9d79c6d6466b86e2612d571`;
channel-add/materialization evidence is
`ev_6d16bea2989f4c63bd2dabf36117c35301a413fa438ec019bd5bc5c4a31ee39b`.
See the Python evidence document for the precise original-call exclusions.

Native unit checks exercise every combination of the four inspected flag bits,
name padding and truncation, vtable/allocation-tail preservation, serialized
holes, opaque payload copying, and invalid exact sizes. Local Windows Zig C++20
compilation with warning flags and the unit executable passed.

The differential runner uses an explicitly supplied synthetic allocation for
every case:

```text
python -m tools.native_lobby_channel_record_compare build/native-check/mco_lobby_channel_record_compare.exe
```

Local Windows differential verification matched 192 constructor images and 224
record images, and rejected six malformed runner inputs. The corpus combines all
flag masks with random unrelated flag bits, six name lengths around the 30-byte
boundary, arbitrary allocation contents, random connection/caller fields, and
32 unconstrained object images. It compares complete images/records, including
untouched bytes, against the original-verified Python implementation.

This native comparison does not execute the original executable or contact a
server. Upstream allocation clearing, authenticated room-argument producers,
socket selection and the complete channel-join lifecycle require separate
recovery and verification. Linux build and live fan-server acceptance remain
separate gates.
