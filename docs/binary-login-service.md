# Binary account login

`client/nps_login_service.py` connects the recovered login encoder, TCP transport
and response parser. It accepts a `PreparedLogin` created after HTTPS
authorization; it does not obtain passwords or tickets itself. The caller must
still supply the unresolved key-record value to `prepare_login` explicitly.

Original function `0x72a8f0` sends the complete 0x501 message, reads one frame
with a 30-second wait, then reads another with a 120-second wait. It labels the
first frame an acknowledgement but does not check its opcode. Only the second
frame is interpreted as the login result. The portable implementation preserves
that sequence on one TCP connection and closes it when the exchange ends.
It does not retry a failed login or treat an acknowledgement as authentication.

| Final reply | Native result | Observed interpretation |
| --- | --- | --- |
| 0x601 | 0 | Login success |
| 0x602 | -11 | User not found |
| 0x610 | -106 | User not authorized |
| 0x623 | -142 | Authorization denied |
| 0x626 | -127 | User banned |
| 0x637 | -141 | Executable CRC mismatch |
| Other | -1 | Unexpected reply |

`LoginSuccess.from_frame` requires 0x601 and the complete 12-byte header before
decoding the existing bounded payload. Short or malformed success replies fail
instead of producing an account. Rejections raise `LoginRequestError` with the
reply ID and recovered numeric result; response bodies are not included.

The returned `AuthenticatedAccount` retains the decoded response and the
original `PreparedLogin` separately. Its `user_id` comes from login success.
The client-generated 32-byte request material is still available for the lobby
cipher and digest; the response's nested key record does not replace it. Neither
record appears in the account object's default representation. Returning this
account means only that the exchange received and parsed the required success
message, not that persona activation, lobby entry, MCOTS login or a race succeeded.

Service tests use synthetic success/rejection replies to check the two receives,
timeouts, identity and key retention, early EOF, and closing on failure. Actual
framing and socket behavior have separate local transport tests. Live account
acceptance and the complete native login routine remain unverified.

REA evidence for the native exchange and rejection switch:
`ev_d467ae0f4f856a7511b66c1db5d6731c6dee0888f10edb8d3bfbf1d281a6d0f4`.
The target is executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
