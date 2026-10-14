# Revival authorization response envelope

A private local connection test on 2026-10-14 reached the configured Revival
HTTPS authorization service and received an HTTP-success body with a compact
hash-pair envelope. The body had no line breaks and used a shape equivalent to
this **synthetic** example:

```text
#Valid#FALSE#Ticket##reasoncode#7#reasontext#synthetic denial#reasonurl##
```

The initial reconstruction handled line records only, and incorrectly reported
this response as a protocol/data failure. `client/auth_protocol.py` now handles
the observed server format directly, preserving empty values, the first value
of duplicate keys, and the existing exact `TRUE`/`FALSE` decision. Success still
requires a nonempty ticket. Malformed, incomplete or mixed envelopes fail before
an authenticated session can be constructed. Ticket and reason text remain
excluded from object representations and exported test reports.

This extension is based on the live service's response structure. It is
**not** claimed as original DLL parser parity. Static Ghidra analysis of the
installed `authlogin.dll` decoder `0x10004090` selects LF record separators and
hash comments; its key/value parser checks equals, space, tab and comma.
The native DLL SHA-256 is
`b4822e997cd86c0890fafb6a395013d61daa413f70880d3e26e8b660a24635f6`.

| Static observation | Evidence |
| --- | --- |
| Authorization response decoder | `ev_eb873425d164758668dbb79e8c12e413329fa795f506646f5a1880eed9582ff7` |
| LF/hash configuration bytes | `ev_8d6e4183054e380812f8aeda76a144712bae656633d296bfd7d512f9db55f45b` |
| Key/value delimiter configuration | `ev_1b54d92ca1b48f167e084aeebf4f0ee2cc79c0bbe3f6cb2a86c4680188735a26` |
| Response record parser | `ev_c845f1a49fe780a6543313d9e42d21b1a9940dd2a02ce5c4ae19b237b3809b6d` |

After the parser correction, the live tester reports `authorization_denied`
at stage `authorization`. No binary account login, persona request, lobby,
primary connection or garage fetch was reached. This demonstrates HTTPS
authorization exchange and decoding of a denial, not successful account or
race compatibility. The server did not report its version. Original-client
comparison with the same account is still required before attributing the
denial to credentials or request incompatibility.

The real body, account input, request target and private response values remain
outside the repository. Tests use authored synthetic envelopes; the report is
an allowlisted local artifact. `fan-server-test-report*.json` is ignored by Git.
