# Persistent MCOTS session

`client.mcots_session.MCOTSSession` combines the verified RC4 primitive,
bounded PKWARE DCL decoder and MCOTS TCP transport. It owns the transport and
two independent cipher states. Its input key is the 32-byte retained client
session material; each cipher schedules its first 16 bytes.

Scheduling is prepared without advancing a stream, while encryption starts
disabled. This permits plaintext attachment. Attachment completion enables
encryption explicitly. Incoming flag 0x08 also enables it, matching native
`0x6f60a0`. Once enabled, subsequent packets without control flag 0x80 are
decrypted even if their individual 0x08 flag is absent. Enabling an already
enabled session does not reset its cipher states.

Incoming payloads are decrypted before flag 0x02 is decompressed. Returned
application frames preserve the transaction ID and remove the consumed 0x08
and 0x02 transform flags. Output remains bounded and reply parsing can operate
on plaintext without accidentally transforming it twice.

The original control values are four-byte little-endian payload values:
0xf216 requests a keepalive reply and 0xf207 is that reply. The session rewrites
0xf216 to 0xf207, preserving any remaining payload bytes and transaction ID,
and sends it with control flag 0x80. This bypasses encryption and leaves the
outgoing stream position intact. Keepalive replies and other control frames
are consumed before returning an application frame. The receive deadline
covers these control exchanges and application waiting together.

Application sends take a plaintext frame and encrypt it when the connection
is enabled. Caller-supplied transform flags are rejected before cipher
advancement. Outgoing compression is still a separate unfinished encoder;
the current send API does not accept a compression request. The protocol
supports these uncompressed envelopes, but this does not establish identical
compression choices to every original gameplay message.

A malformed transformed payload or failed I/O closes the transport and clears
both cipher states. Caller validation failures leave the stream position
unchanged. One instance requires serial access, matching its socket owner;
concurrent application calls are not supported.

Real local socket tests cover persistent encryption when a later flag is
absent, decrypt-before-decompress, plaintext attachment then activation,
multiple encrypted sends, keepalive response bytes, preservation of both
stream positions across a control exchange and closing after malformed
compression. All 281 local repository tests passed. The individual cipher
and compression algorithms have separate original-code oracles; the combined
session checks use synthetic peers and do not establish live fan-server
acceptance.

Primary attachment/login orchestration is now implemented in the
[primary service](mcots-primary-service.md). Service descriptor configuration, outgoing
compression and the full transaction/race services remain incomplete. This
session does not perform authentication by itself.

Native transformation-order evidence:
`ev_474369a9f3f966f86b4b6d795b994fc1ab85abd91c1d5e89ed3caf9613e3096d`.
See [compression](mcots-compression.md), [encryption](mcots-encryption.md) and
[transport](mcots-transport.md) for the recovered boundaries and verification.
