# Primary MCOTS attachment and login exchange

`client.mcots_primary_service.connect_primary` integrates the recovered
primary transaction steps. It validates the login record, retained 32-byte
client session material, transaction ID and timeouts before opening a socket.
The caller supplies the transaction endpoint from shard discovery and explicit
values for the three still-unresolved native login fields.

The exchange sends the 40-byte 0x1b6 attachment payload as plaintext, waits
for a matching generic completion, then enables both persistent cipher
directions. A rejection closes the connection without sending login. It sends
the 39-byte 0x69 login record encrypted, using the next uint32 transaction ID,
and waits for a matching, bounded 0xd5 success payload. Keepalives are handled
by the session layer while waiting. Transaction increment wraps at uint32,
matching the original allocation counter arithmetic.

A generic login acknowledgement alone is insufficient for this API: it cannot
supply the fields and service records the original handler subsequently
reads. A truncated or mismatched rich reply also fails and closes the session.
`MCOTSPrimaryRejected` retains the stage and numeric server code without
including account names, keys or passwords in its message.

The result, `MCOTSPrimaryLogin`, owns the accepted primary response and open
session. Its context manager closes that session and both cipher states.
This result specifically represents the primary exchange. It does not claim
that the follow-up services advertised by the response have been connected or
attached, that the original game's complete login flow is done, or that a
live fan-server account was accepted.

The default transaction ID is zero, as in the recovered communication
configuration. Callers can supply a starting value explicitly. Native IDs are
allocated for other internal messages too, so the portable exchange does not
claim to reproduce every allocation's global sequence. Replies are correlated
to the IDs actually sent. Connect, attachment wait and login wait have separate
configurable timeouts; requests are never automatically retried.

Real local TCP tests verify exact plaintext attachment bytes, encrypted login
bytes, independent incoming/outgoing streams, a control keepalive exchange,
the rich response and ownership cleanup. They also cover uint32 wraparound,
attachment rejection, wrong transaction IDs, missing/truncated login data,
and validation before connection. All 286 repository tests passed locally.
The algorithms and packet builders have separate original-code oracles;
the integrated exchange uses a synthetic peer and does not prove live server
compatibility.

Remaining integration includes service descriptor configuration and attachment,
account-to-primary orchestration, native login-field meanings, UI lifecycle,
outgoing compression and full transaction/race behavior. See
[login success](mcots-login-success.md), [session](mcots-session.md) and
[attachment replies](mcots-responses.md) for the recovered boundaries.
