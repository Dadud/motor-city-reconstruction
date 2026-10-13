# Original post-login data sequence

Primary acceptance is followed by data-manager setup and account data work in
the installed client's `0x5ef240` caller. These operations must be recovered
before the reconstructed client can populate the original garage and menus.
This document records static call relationships; it does not claim live server
acceptance or assign names to data whose consumers remain unresolved.

The first calls are local lifecycle work: `0x4bd7a0` destroys the manager's
existing objects, and `0x4bd320` allocates twelve replacements. Procedures
`0x4bab00` and `0x4baf20` mark their objects for refresh. Thus these addresses
are not themselves transaction opcodes or network requests.

| Refresh entry | Submission entry | Local queued operation | Packet builder |
| --- | --- | --- | --- |
| 0x4ba850 | 0x4bab20 → 0x65f520 | 0x144 | 0x65f4b0 |
| 0x4bac70 | 0x4baf40 → 0x65f8e0 | 0x142 | 0x65f870 |
| 0x4bb980 | 0x4bb940 → 0x660ad0 | 0x198 | 0x660a00, local cache path |
| 0x4bbde0 | 0x4bbda0 → 0x65fcd0 | 0x16b | 0x65fc60 |
| 0x4bc220 | 0x4bc1e0 → 0x65ff00 | 0x185 | 0x65fea0 |

The four network builders allocate ten payload bytes through `0x6833c0`,
write their little-endian operation word, and queue through `0x683390`, which
routes to primary service 0xfe. Operation 0x142 additionally writes a uint32
argument at payload +2; the caller shown here supplies zero. Remaining payload
bytes inherit allocator initialization. The direct response layouts are now
decoded by `client.mcots_data_response.MCOTSDataReply`; integrated fetching and
the meanings of individual fields remain incomplete.

| Request | Direct reply | Layout |
| --- | --- | --- |
| 0x144 | 0x145 | uint16 count +2, continuation byte +4, 569-byte records +5 |
| 0x142 | 0x143 | Same list header, 8-byte records |
| 0x16b | 0x16c | Same list header, 516-byte records |
| 0x185 | 0x186 | 118 bytes, including the operation word |

The parser requires the matching transaction and expected reply operation,
checks the entire counted record span before slicing, and retains trailing
extensions. A nonzero continuation byte means more pages; it is not restricted
to literal 1. Records remain opaque until their consumers establish meanings.
Generic failure replies are handled separately, not interpreted as data.

Native list assembly has important differences. Handler `0x65f190` appends
0x145 records at the previous record count times 569. On its final page it
finds duplicate first-uint32 values and zeroes later duplicates' first words.
Handler `0x65f5a0` appends the 8-byte 0x143 records. Handler `0x65f9a0` copies
0x16c records to the allocation's base each time, while increasing its stored
count; it does not use that count as a destination offset. The portable parser
retains individual chunks and does not silently replace this behavior with
ordinary concatenation.

`client.mcots_data_assembly.MCOTSDataAssembler` now assembles matching pages.
It appends 0x145/0x143 records, applies final-page duplicate-ID clearing to
0x145, and reproduces the base overwrite for 0x16c. The result's count includes
all received records, as in the native handler. Any resulting slot never
written by a page is represented by `None`, retaining uncertainty rather than
inventing data. Allocation helper `0x65e910` uses an uninitialized heap buffer
on its large-allocation path; bytes in such unwritten slots cannot be recovered
from the network response. Previous records beyond an overwritten prefix are
preserved. The 0x186 fixed reply completes in one page.

Extensions are retained per page. Invalid identities, malformed lengths and
resource-limit failures leave the previous accepted state intact. Default
limits of 16 MiB and 1024 pages are portable defensive limits, not recovered
native constants. Feeding a completed assembler fails. The assembler itself
does not send requests or interpret typed garage fields.

`client.mcots_data_service.MCOTSDataClient` now provides serial requests on an
accepted primary session. The caller supplies the next unused transaction ID;
each issued request consumes it and wraps at uint32. The four supported
request payloads are ten bytes. Operation 0x142 has its argument at +2; the
others have only their operation word and zero bytes from the normal pool's
initialization path. The native pool's exhausted-allocation fallback does not
have the same clearing step; reproducing stale/debug-fill bytes from that
exceptional path is outside this encoder.

`fetch` sends one request and assembles direct reply pages under one overall
deadline. Unrelated transaction frames are retained in a bounded FIFO,
retrievable with `pop_pending`. Operation 0x198 cache updates are retained even
when their transaction matches, because the original handler treats them
independently. Existing session keepalive and encryption handling continue
while waiting. A generic successful acknowledgement without a data record
cannot complete fetching. A correlated rejection exposes the operation and
numeric code and leaves the connection usable; malformed matching data,
timeouts, transport failures and resource-limit failures close it. There are
no automatic retries.

Real local TCP tests use independently encrypted peers to verify a two-page
reply, unrelated-message retention, a cache update, a control keepalive,
transaction wraparound and a second fixed reply on the same stream. A second
exchange verifies rejection followed by another successful request. These
synthetic peers verify the authored exchange, not live fan-server acceptance.
Typed garage records, the full initial-fetch sequence and cache consumers
remain unfinished.

Confirmed record views are available in `client.mcots_data_records`. These
names describe offsets and observed operations rather than assigning guessed
business meanings:

| Record | Confirmed consumer fields |
| --- | --- |
| 0x145 / 569 bytes | ID +0; uint32 +4; C-string start +0x0c; byte flag +0x2c; uint32 reference +0x137 |
| 0x143 / 8 bytes | Two uint32 values; consumers filter on the second and return the first |
| 0x16c / 516 bytes | ID +0; `0x4bebb0` returns a pointer to the remaining 512 bytes after an ID match |
| 0x186 / 118 bytes | Three uint32 values +2/+6/+10; doubles +0x1e/+0x26 |

The +0x0c text view exposes a bounded 32-byte window ending before the known
flag. Consumers compare a C string from that start, but its full declared
capacity remains unresolved. Original narrow bytes are retained without
guessing a text encoding. The two double readers use fallback values 0.1
and 0.75 only when the entire native result is absent; those numbers are not
defaults for missing or invalid fields inside a received record.

The common 0x145 eligibility predicate requires nonzero ID, +4 value,
+0x137 reference and +0x2c flag, a successful external reference lookup, and
either a nonempty text start or +4 value equal to 14. Its reference membership
comes from the separate list searched by `0x58bc30`; this module requires the
caller to supply that result rather than assuming every reference is known.
The simple lookup `0x5e89a0` instead returns the first ID whose +4 value matches
the query, without those eligibility checks. A matching zero ID still returns
zero and stops; it does not skip ahead to a later nonzero match.

`python -m tools.mcots_data_lookup_oracle /path/to/original/mcity.exe` executes
that original lookup with a controlled already-fetched result. Four cases
(empty, middle match, first zero-ID match and no match) agree with the portable
lookup. The refresh call is substituted; no network, allocation or membership
lookup executes. Actual record business meanings and cache-backed UI behavior
remain incomplete.

`python -m tools.mcots_data_copy_oracle /path/to/original/mcity.exe` checks
the original 0x145 and 0x16c copy instructions with zero, one and three records,
including a nonzero previous count. All six cases matched every byte of an
8192-byte destination, demonstrating the append/overwrite distinction and
the final partial-word copy for 569-byte records. The bounded oracle stops
before allocation or status publication; no sockets run. Four additional
bounded executions of the original final-page duplicate loop compare zero
IDs, unique IDs and repeated IDs against portable duplicate clearing. Those
four cases also match, including preserving record tails after clearing only
the first four bytes.

Operation 0x198 illustrates why a queued operation cannot be assumed to be a
wire request. Its handler `0x660a00` checks global cache `0xb29730`: a zero
state registers pending local work through `0x6835e0`; a small nonzero status
is returned directly; a populated cache is copied into a new owned result.
This handler does not build or send an MCOTS packet. Completion `0x660860`
replaces that cache from an incoming counted 8-byte list, then satisfies pending
local work by operation rather than a request packet's transaction. Dispatch
and the list's business meaning still need tracing.

The later `0x5efd60` sequence refreshes additional objects, reads account data
at several unaligned offsets, chooses a car, and updates local presentation.
Its data schemas and request paths remain incomplete. Reproducing only the
primary acknowledgement cannot satisfy that sequence.

Evidence includes `ev_e0e2fbfea89f59742bfd0e308fb8524acae3f658568994865422d3c4f50b92c9`
(manager construction), `ev_07c2e903bc72b5a17e5d8dc683e38f12341bbc38c44c0bc35b0c6767e0333966`
(0x144 builder), `ev_85e756b9507f7a904b7b2feaa27abe4329c208c7ae53062bbb0461e93b74fcd0`
(0x198 cache handler), and `ev_8d8bc0b11a05e1836fb6d4e2af20cc80029edc487b61c844929595ce87bb10af`
(later initialization). Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

Reply-handler evidence:
`ev_4a4fffb9659c33f87e1094577ae61e6646a6e6d72ed81a006bb463ffcaf055f9`
(0x145), `ev_a4e44457c355d9a456032c58c4371e1adad1a851477df3c0d133fbb3b50513f3`
(0x143), `ev_85af5f8ed88ce0b034950e94df4ac769b930c6b1117831aad8bcf3e713411163`
(0x16c), `ev_a50cdc698fac002a65376de8012d90498c58ccb468263460c995b1b794573dbd`
(0x186), and `ev_0d1ba3461d9bb86c890533af74a2c4e0da6e0dc4b3e75624eeb3150f7749fc1d`
(cache replacement). These are static observations except for the specifically
bounded copies tested above.

Allocation evidence:
`ev_51e623d856b89fa283f75c5cb2684ed069de89ffb206e154f7b4f26a0662f7d7`.

Consumer evidence: `ev_293e0e005ec8ab1d4c99bcbd8532018ecc59309ab3b6290e393832c8e169e094`
(eligibility), `ev_ddd1037ee7b81741a9d42b29f2e16ff2dff399153ef22cdd54954817382d2ade`
(simple lookup), `ev_e6b50fc3658ebc1c7c46e91ca758fe02849a64948964a98df8d8118599d8f550`
(8-byte pair filter), `ev_8467780928961ecb4191b498a707da2730dd26b25d8f82dde32367a141c96502`
(516-byte ID lookup), `ev_166b10dca831f4238ca0448c157f99e6c70e9189dc105ba85ab2affb688a0387`
(three fixed values), `ev_6f17ecfcb0a9998a06763d41c085be418f0e2f0468fb3f930891ef636970d400`
and `ev_3638ed0937b0a1e65d734e43ddca6a9a296da364ec3f61ff25ebb41933fb6ad6`
(double readers).
