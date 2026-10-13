# MCOTS TCP transport

`client.mcots_transport.MCOTSConnection` provides an explicit persistent TCP
connection for the recovered little-endian MCOTS envelope. `connect` uses a
supplied endpoint; `send` validates one complete encoded frame; `receive`
consumes exactly one frame and leaves the next frame in the stream.

Payload transformation and reply dispatch remain caller responsibilities.
An encrypted frame is returned with its ciphertext and flags intact. This
transport does not automatically authenticate, initialize cipher states,
retry transactions or connect the services in a login reply. Those layers
must use the recovered attachment and login behavior.

The receive deadline covers the two-byte length, nine remaining header bytes
and payload together. Marker validation occurs before waiting for payload
bytes. A malformed frame, truncated stream, receive timeout or socket error
closes the connection because its byte position can no longer be trusted.
Invalid caller arguments are rejected before I/O and leave the connection
usable. These complete-read deadlines and strict frame bounds are portable
hardening; they are not claims that the original used identical timeout
handling.

The class shares socket creation and cleanup with the existing NPS transport,
but overrides both framing methods. It never applies NPS big-endian frame
rules to MCOTS traffic. Maximum MCOTS payload is 65,526 bytes, because the
16-bit length adds nine and excludes its own two bytes.

Tests use real local sockets for byte-by-byte fragmentation, consecutive
frames, invalid markers, EOF, partial-payload timeouts, exact sends and a TCP
connect/context-cleanup cycle. All 269 repository tests passed on the local
Windows host after this addition. Local peers do not establish compatibility
with the live fan server.

## Transaction value and follow-up services

Allocator `0x6f9d40`'s dynamically allocated message path copies the current
shared counter into allocation +0xf and increments that counter. This
corroborates the reply dispatcher's use of the value as a transaction ID.
The pooled allocation path calls `0x6f9a40` and needs its own initialization
trace before reproducing the original initial counter and reuse behavior.

Service follow-up routine `0x682b60` constructs the same 40-byte operation
0x1b6 attachment record as the primary attachment. It retains session bytes
in a local task and queues the request through the primary service 0xfe.
The retained task records the target service ID, which the completion handler
uses to initialize encryption on that target connection. Therefore a service
attachment request is not simply sent to whichever socket it configures.
Complete integration still needs the target descriptor configuration and
the dispatch behavior around these service requests.

Evidence:

- Counter allocation: `ev_4f9cbb4c5124c713f0e046a6219c798ab04e31048ee721e439daf721b3e5c4e1`.
- Follow-up attachment: `ev_bd251cc9ddd2cb11da86df8ec6f3ccebf5c3c8fa5fda54ff4a90407a98997034`.
- Service status access: `ev_7557cf61cc4b2511b2d65ef68d5cac1dd8b5230551a446009c3d48c2d7c8abf0`.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
