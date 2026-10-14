# Account, lobby and primary connection flow

`client/online_account.py` joins the recovered services into an explicit,
blocking developer API, including the primary MCOTS exchange. The game's
menus, follow-up services and racing remain unfinished.

## Private local verification

The account check tool prepares the configured public shard and external identity
without prompting for credentials by default:

```sh
python -m tools.account_check '/path/to/Motor City Online' --shard-id 44 --source nps/shardlistip.ini
```

The installed top-level and NPS discovery files may name different URLs; select
the exact installed source explicitly when they differ. On Linux, additionally
supply the original configured `--auth-host` and `--auth-service`; the installed
certificate pin remains required. Do not guess the auth host from binary ports.

Add `--login` in an interactive local terminal to perform one authorization,
binary login and persona retrieval. Both account name and password are entered
with hidden prompts. Credentials are not accepted as command arguments or saved
to files; account payloads, names, tickets and key material are omitted from
output. Redirected input and an echoing input fallback are rejected. Ctrl+C
stops the check. Network errors expose their type without private exception
details. Python retains credential strings in process memory during the request;
this tool makes no memory-erasure guarantee.

The resulting report distinguishes public preflight from a live account test.
It does not select a persona, enter the lobby, load a garage, modify inventory or
race. Local validation on 2026-10-13 passed configured shard 44 public discovery
and identity prerequisites; no account credentials were supplied. Automated
tests use synthetic accounts and check cancellation and secret-free diagnostics.
Full live compatibility remains unverified.

`authenticate` receives an external installation, discovered shard, configured
auth settings/certificate pin and credentials. The key-record value defaults
to the [recovered startup zero](nps-key-initialization.md); an explicit research
override remains supported.
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

`enter_connections` performs that same activation and lobby sequence, then
connects to the discovered transaction endpoint with the same account ID,
selected persona and retained 32-byte client key. It passes zero for all three
extra login fields, matching the original caller. It validates primary inputs
before activation. Primary failure closes the accepted lobby; the returned
`OnlineConnections` context manager owns and closes both accepted streams.
It stops at the primary rich success reply, before additional service joins
and game-data requests.

Original caller evidence: procedure `0x5ef240` clears EBX at `0x5ef2e8`, has
no subsequent EBX writes before the three pushes at `0x5ef815`, `0x5ef81c`
and `0x5ef822`, and invokes `0x683100` at `0x5ef857`. The Windows x86 calling
convention preserves EBX across intervening calls. Thus the three values are
zero in this path; their broader meanings remain unresolved. Local REA evidence
ID: `ev_f6fc96430dcc6cdc39dc51c7dd405281738d905606779b9a9e3e0a5690f3143d`.

The explicit key-record value remains unresolved in original runtime evidence;
the integration does not introduce a guessed default. Hostname and local IP
encoding are also caller supplied. This API sends account and activation requests
only when explicitly called; importing it performs no network I/O. The online
game UI, cancellation/background execution and reconnect policy remain unfinished.

Tests verify ticket handoff, service ID, account/key retention, stopping after
denial, shard-aware selection, account-versus-persona identity, and rejecting
invalid local identity fields before activation, ordered primary handoff and
cleanup after primary rejection. They use synthetic service
results. Separate TLS and socket checks exercise the transport, but the complete
flow has not yet succeeded against an authorized fan-server account.

See [HTTPS authorization](https-authorization.md),
[binary login](binary-login-service.md), [persona operations](persona-protocol.md),
and [lobby service](lobby-service.md) for original instruction evidence and
verification scope of each stage.
