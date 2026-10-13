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
bytes inherit allocator initialization. Response layouts and ownership must
be traced before providing an integrated fetching API.

Operation 0x198 illustrates why a queued operation cannot be assumed to be a
wire request. Its handler `0x660a00` checks global cache `0xb29730`: a zero
state registers pending local work through `0x6835e0`; a small nonzero status
is returned directly; a populated cache is copied into a new owned result.
This handler does not build or send an MCOTS packet. The cache producer still
needs tracing.

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
