# Account-to-lobby flow

`client/online_account.py` joins the recovered services into an explicit,
blocking developer API. It does not replace the game's menus or implement
MCOTS and racing.

`authenticate` receives an external installation, discovered shard, configured
auth settings/certificate pin, credentials and the explicit key-record value.
It checks the external public key and executable identity before transmitting
credentials, obtains an authorization ticket, prepares binary login, requires
login success, then requests the account's persona list. A failed stage stops
the sequence without retrying or automatically choosing a persona.

The resulting `OnlineAccount` contains the discovered shard, authenticated
account response/retained client material, and decoded persona list. It stores
neither username nor password. Account and persona contents are omitted from
its default representation. A denial exposes a generic message and retains the
server's reason code separately; private reason text is not included.

`enter_lobby(persona_id, hostname=..., ip_address=...)` searches the downloaded
list using both persona ID and the selected shard ID. It validates the lobby
identity fields, activates the selected persona, then opens the lobby using the
authenticated account ID and retained client request key. The raw map record's
account field cannot replace the authenticated identity. The returned lobby
connection belongs to the caller and must be closed after use.

The explicit key-record value remains unresolved in original runtime evidence;
the integration does not introduce a guessed default. Hostname and local IP
encoding are also caller supplied. This API sends account and activation requests
only when explicitly called; importing it performs no network I/O. The online
game UI, cancellation/background execution and reconnect policy remain unfinished.

Tests verify ticket handoff, service ID, account/key retention, stopping after
denial, shard-aware selection, account-versus-persona identity, and rejecting
invalid local identity fields before activation. They use synthetic service
results. Separate TLS and socket checks exercise the transport, but the complete
flow has not yet succeeded against an authorized fan-server account.

See [HTTPS authorization](https-authorization.md),
[binary login](binary-login-service.md), [persona operations](persona-protocol.md),
and [lobby service](lobby-service.md) for original instruction evidence and
verification scope of each stage.
