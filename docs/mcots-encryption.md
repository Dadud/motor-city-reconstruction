# MCOTS attachment and encryption

The transaction connection uses a different cipher from the lobby. MCOTS
initializes two RC4 contexts with a 16-byte key, with no initial keystream
discard. Each direction retains its permutation and indices across payloads.
The 11-byte TCP envelope remains outside the encrypted payload.

## Key source and activation

Attachment builder `0x682090` constructs a 40-byte native payload, operation
0x1b6. It also retains a local task containing the service ID, account ID,
persona ID, name, session-byte length and session bytes. The key bytes are
copied into that task at +0x20. They are not copied into the attachment payload.

| Payload offset | Bytes | Value |
| --- | --- | --- |
| 0 | 2 | Operation 0x1b6 |
| 2 | 4 | Account user ID |
| 6 | 4 | Persona ID |
| 10 | 13 | Zero |
| 23 | 12 | Persona name, `strncpy` truncation or NUL padding |
| 35 | 1 | Explicit NUL |
| 36 | 4 | Literal 0x1b5a |

Completion handler `0x681d30` finds the pending transaction by the four-byte
value at allocation +0xf. In its positive completion branch, it passes the
retained task's bytes at +0x20 to `0x6f6c20`, then enables connection encryption
through `0x6f6b50`. The generic success and wrapped-result conditions are
recovered in [MCOTS replies](mcots-responses.md). Their bounded verification
does not establish that a real fan server accepted an attachment.

`0x6f6c20` locates the connection and calls `0x6fa730`. That initializer
constructs two RC4 objects through `0x6fd320`, each with the same key pointer
and fixed key length 16. Its second argument is not used by the recovered
initializer. Thus both directions use the first 16 bytes of the retained
client session material. The login-service returned key record does not
replace those retained bytes in this path.

## Calculation and stream lifetime

The constructor fills a 256-byte permutation with values 0 through 255. For
each index i, it computes j = (j + S[i] + key[i modulo 16]) modulo 256 and
swaps S[i] with S[j]. Both stream indices then start at zero.

For each payload byte, `0x6fd820` increments i modulo 256, adds S[i] to j
modulo 256 and swaps S[i] with S[j]. The byte is XORed with
S[(S[i] + S[j]) modulo 256]. This is standard RC4 scheduling and generation.
The sender `0x6fa7f0` applies the outgoing context to allocation +0x14 for the
declared payload length, so the TCP envelope is not part of the cipher stream.
It does not recreate the cipher for each message.

`client.mcots_cipher.MCOTSCipher` implements the recovered primitive and
requires an explicit 16-byte key. It validates a payload before advancing
state. Connection attachment, response dispatch and automatic selection of
encrypted versus plaintext messages remain separate work.

## Verification and limits

`python -m tools.mcots_cipher_oracle /path/to/original/mcity.exe` runs the
original permutation fill and scheduling range `0x6fd386`–`0x6fd46d`, including
the original accessor and swap helpers. It then runs the original processing
routine `0x6fd820` on three successive payloads for each key. Three key
schedules and nine stream calls matched the portable implementation, including
the full permutation and both indices after every call. This validates
persistent state as well as output bytes. Allocation, OS imports, attachment
and network I/O are excluded.

Static evidence:

- Attachment builder: `ev_e8f3130021a9e8fb18ee936081b049d78b615edd548b4d9daef68fafeb5facec`.
- Completion/key source: `ev_35c6063a38c3adabcab8d0aec092dfe66f373e82c7e2e0bfc314508360dafb49`.
- Connection lookup: `ev_0205fc9a09f0479cc29812ecab30f1af75c1dcf1cc6ccf3c4fa81660bc92e0be`.
- Two-context initialization: `ev_611f535a994175d7b55c92d63119d8f24c7aa560e23aac9cedcc369d17bffae1`.
- RC4 scheduling: `ev_967d22cc517c6a1245213fe113c7ff22243437182ba75b5570093fa85b097388`.
- RC4 payload processing: `ev_1d2f1a26b1d6da6b72b972bf73773deb3f464e8fd41a344acb285171efb118c9`.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
