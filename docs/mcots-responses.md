# MCOTS transaction replies

The envelope's four-byte value at wire +6 is used to match a response to a
pending transaction. `0x683840` searches the pending list for that value and
returns the original operation. Dispatcher `0x65dcd0` uses that operation to
select the completion handler from the table at `0x8be6b0`.

The table entry at `0x8bf118` contains operation 0x1b6, local request handler
`0x682440`, and completion handler `0x681d30`. The request and response
handlers are separate table columns. This identifies the positive branch
that initializes the RC4 contexts after attachment.

## Generic completion forms

| Payload opcode | Completion rule |
| --- | --- |
| 0x65 | Success; resolve original operation by pending transaction |
| 0x66 | Failure; 32-bit result code at payload +4 |
| 0x107 | Failure; 32-bit result code at payload +4 |
| 0x67 | Wrapped result: original operation at +2; code at +4; success iff code is 0x65 |

Integers are little endian. In the direct 0x65 case, the generic dispatcher
does not interpret bytes +2 as an original operation. Those bytes may belong
to the operation-specific success record. If the pending transaction is
missing, the native dispatcher falls back to the 16-bit field at +2. The
portable parser instead requires an explicit matching pending transaction.
For 0x67, it additionally rejects a wrapper operation that conflicts with that
pending request. These are deliberate bounds and correlation checks.

The receive pump `0x65dd80` recognizes wrapper 0x67, reads its original
operation at +2 and compares its 32-bit result at +4 with 0x65 before dispatch.
Unknown operation-specific replies are not silently treated as success by
`client.mcots_response.decode_completion`; they require their own parser.
It expects a frame whose payload has already been decrypted/decompressed.

## Attachment status

The attachment completion handler removes the matching pending record before
handling the result. A positive result initializes encryption from the
retained session bytes and enables it on that connection. Its native status
is 1 after initialization succeeds. Failure codes map as follows; labels for
the original numeric statuses remain unresolved.

| Server code | Native status |
| --- | --- |
| 0x6b | 0x60 |
| 0x7c | 0x5d |
| 0x82 | 7 |
| 0x83 | 0x5e |
| 0xba | 0x5f |
| 0xbb or 0x1b4 | 0x5a |
| 0xbc | 0x5c |
| Other | 3 |

`attachment_status` reports the decoded server outcome. It does not perform
the subsequent native key initialization or establish an authenticated
connection. A network service must complete those steps before reporting
successful attachment to the caller.

## Verification and remaining login work

`python -m tools.mcots_response_oracle /path/to/original/mcity.exe` executes
the original generic dispatcher for 0x65, 0x66 and 0x107. It supplies a pending
attachment record and stops before the attachment handler. All four handler
arguments matched, including the resolved operation's handler and success
boolean. It also executes the original attachment failure branches for 12
codes, stopping before the free routine executes. All mapped statuses matched.
No network calls or key initialization execute in this bounded oracle.

Login operation 0x69 uses handler `0x682590`. That handler recognizes an
operation-specific 0xd5 payload and reads fields through offset 0xa9, including
four service records starting at +0x21 with a 26-byte stride. This is a richer
success response than generic acknowledgement. Its complete layout, service
attachment behavior and bounded parser remain to be recovered before the
portable client can enter the transaction services faithfully.

Evidence:

- Generic dispatch: `ev_82949101a596cb33bb1771924f4e8f06bb54d19f48594f5d8ef853a03c4683b2`.
- Receive pump/wrapper: `ev_6f9374a6ce7b579b7174628b965bfb0c8597d1f9a45e4d40f6cca0f74673314d`.
- Pending lookup: `ev_ca4fc496f1baef17d15b8ad11f20d3ea721ec31984349fe4887aebb05e04b2e2`.
- Attachment completion: `ev_35c6063a38c3adabcab8d0aec092dfe66f373e82c7e2e0bfc314508360dafb49`.
- Login completion: `ev_42b9b05a5ddaf57e495d100245468a26374f6a5685a855ee46fa0bd9e6986d3f`.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
