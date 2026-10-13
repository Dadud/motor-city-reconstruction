# HTTPS authorization request

`client/auth_service.py` performs the recovered ticket request when explicitly
called. It receives the configured auth host/base service, installed certificate
SHA1 pin, username, password and service ID. Importing the module performs no
network I/O. A returned authorization ticket still needs the binary login
exchange described in `binary-login-service.md`.

The original `authlogin.dll` routine at `0x10001fa0` uses WinINet's
`InternetOpenA("AuthLogin", ...)`, connects to HTTPS port 443, builds the query,
and requests HTTP/1.0. It calls `HttpSendRequestA` without an additional body,
accepts HTTP status 200 through 299, and reads the response in 4000-byte chunks
before parsing its text. The portable service preserves the HTTP version,
user agent, core query order and successful-status range. It uses the existing
password encoder and ticket parser recovered from that DLL.

The configured certificate pin is verified before HTTP request bytes are sent.
The service closes its connection on completion or failure, does not follow
redirects, and does not retry requests. Its response read is bounded at 64 KiB
plus one detection byte; oversized responses fail. HTTP error responses expose
their numeric status only. Connection failures expose a generic error rather
than a credential-bearing URL or server diagnostic. Ticket and reason text are
hidden in the returned response object's representation.

Native WinINet redirect, proxy, certificate and error handling are not reproduced
in full. The portable implementation uses the exact installed pin and direct
HTTPS connection, and adds explicit `Host` and `Connection: close` headers.
Printable ASCII credentials and restricted query tokens remain the supported
encoding. Optional `clientIP` and `igrID` query fields remain unimplemented.
The configured timeout applies to socket operations; it is not a total deadline
across name resolution and a slowly delivered HTTP body.

Tests verify query encoding, HTTP version, user agent, certificate-before-request
ordering, failed pin behavior, response bounds, denial parsing, non-success
statuses and sanitized errors. They use synthetic connection responses. The
installed fan server's pinned TLS certificate was checked separately; a real
successful account ticket has not been obtained by this service.

Retained DLL evidence:
`ev_6ce86436747de248e3b58b54d1288ab8b5ff4c608b8636e5e2a44b817b0b106c`.
Source SHA-256:
`b4822e997cd86c0890fafb6a395013d61daa413f70880d3e26e8b660a24635f6`.
