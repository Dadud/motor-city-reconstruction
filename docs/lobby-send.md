# Original encrypted lobby send path

The installed client targets MotorCity Revival at `mc.novaserv.cc`. These
findings describe its executable, not a completed authenticated server test.

The send thread at `0x7378f0` first checks the queued message's encryption flag,
the connection's cipher buffer, and selector `0x7381f0`. That selector excludes
heartbeat IDs `0x207` and `0x217`; other IDs pass. Encryption still depends on
connection state, so passing the selector alone does not enable encryption.

For TCP, instructions `0x737b7f` through `0x737bc0` copy exactly the inner
message's declared length into the reusable scratch buffer. They submit
`(length + 7) & ~7` bytes to the encryption filter. No clearing of the extra
bytes occurs in this branch. The resulting ciphertext is drained back into the
same buffer. Consequently, a later message's tail can contain previous buffer
contents. Initial allocation contents have not been established.

This differs from calling the cipher filter with a partial final block: its
separately verified tail handler acts like zero padding. The TCP sender submits
complete blocks, so that handler does not establish the sender's padding value.
The reconstruction requires explicit tail bytes in `encrypt_envelope`; it does
not read uninitialized host memory or silently label zero padding as native.

Builder `0x7e4560` puts a four-byte big-endian prefix ahead of the ciphertext:
ID `0x1101`, followed by the total wrapper length. The encrypted inner message
retains its own prefix. CBC chaining continues across messages in the current
connection; caller-managed send and receive cipher contexts remain separate.

Synthetic tests cover exact prefix bytes, opaque tail preservation, multiple
messages on the same CBC chain, heartbeat selection, and validation before
cipher state advances. They do not prove fan-server acceptance. Connection
setup, reconnect/reset behavior, authenticated login, and gameplay exchange
still need integration and live verification.

Evidence is static Ghidra analysis of executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`:

- Send thread: `ev_6f47174733196cacc3cf9ce3fd296642e65a29a163996ac80174d7b2c878d677`.
- Selector: `ev_5daa0b8ed981f7eaa26d299a434041acabe3950798bcd09689529666dc783adc`.
- Wrapper builder: `ev_c96beb3921003876a3eb32718544fef64e11150c3cab72a6732fbefeba18b008`.

Raw decompiler evidence remains local and excluded from the public repository.
