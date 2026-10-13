# MCOTS compression and incoming transformation order

Native wrapper `0x6faa00` calls the installed `IMPLODE.DLL::implode` export.
Decompression wrapper `0x6faab0` calls `IMPLODE.DLL::explode`. This is the
PKWARE Data Compression Library format, distinct from ZIP's similarly named
compression method. The portable decoder is an altered Python adaptation of
[Mark Adler's blast 1.3](https://github.com/madler/zlib/tree/master/contrib/blast),
with its complete license notice preserved in `client/pkware_dcl.py`.
No original DLL bytes or recovered proprietary decompressor code are included.

## Incoming order and state

Incoming handler `0x6f60a0` first deals with connection encryption state.
Receiving flag 0x08 enables encryption if that connection was previously
disabled. Once enabled, every incoming payload without flag 0x80 is decrypted
through the persistent incoming context, even when the individual packet's
0x08 flag is absent. A missing or uninitialized cipher closes the connection.
Thus testing only each packet's 0x08 bit would corrupt later messages.

After decryption, flag 0x02 selects decompression. The first two plaintext
payload bytes give the output length as a little-endian uint16. The compressed
DCL stream begins at payload +2. The handler allocates the declared output
size and checks that decompression produced exactly that many bytes. The
portable `decompress_mcots_payload` checks the prefix and output bound before
decoding and rejects a mismatched length.

The native wrapper is passed the allocation's full payload length alongside
a pointer advanced two bytes. The portable decoder bounds its input to the
actual remaining payload bytes, avoiding a possible two-byte read beyond the
frame. DCL stops at an explicit end code; trailing bytes after that code are
ignored, consistent with the decompressor's end-marker behavior.

Control flag 0x80 bypasses encryption. The handler recognizes the four-byte
payload values 0xf216 and 0xf207 as keepalive traffic after transformations;
0xf216 is rewritten to 0xf207, marked 0x80 and queued for return. These control
paths and automatic connection-state handling are not yet integrated into
the portable transport.

## Decoder and verification

The decoder supports uncoded and Huffman-coded literals, dictionary selectors
4, 5 and 6, length/distance pairs and overlapping copies. Both input and output
are bounded by the MCOTS envelope's maximum 65,526-byte payload. Truncation,
invalid headers, distances before output, output overflow and inconsistent
declared length raise an error instead of returning a partial payload.

The published upstream example `00 04 82 24 25 8f 80 7f` decodes to
`AIAIAIAIAIAIA`, including an overlapping copy. Tests verify that vector,
every truncation of it, malformed headers, trailing bytes and MCOTS length
checks. All 274 local repository tests passed after this addition. This
initial vector coverage has now been supplemented with the native comparison
below. No live compressed fan-server reply has been verified.

`python -m tools.pkware_native_oracle /path/to/original/IMPLODE.DLL` maps the
exact hash-verified original PE into Unicorn without executing its DLL entry
point or loading it into the host process. It executes the original `implode`
and `explode` exports with bounded memory read/write callbacks, work memory
and instruction/time limits. All 18 cases matched: literal modes 0 and 1,
dictionary sizes 1024, 2048 and 4096, overlapping copies, all 256 byte values,
and repeated data longer than the 4096-byte decoder window.

The original compressor's outputs for those synthetic inputs are retained in
`tests/fixtures/pkware-native.json`. Ordinary regression tests decode these
fixed streams without the original DLL or optional emulation dependencies.
This checks the coded-literal table independently of a test encoder derived
from the portable decoder. All 275 local repository tests passed with these
fixtures. It remains a bounded CPU emulation comparison, not native Windows
DLL execution or a fan-server acceptance test.

Original DLL SHA-256:
`349a62749766d1a8f9fe6e7bdd13b0cad67959c7454223557cae286c637c06d3`.

Evidence:

- Compression wrapper: `ev_7b249afff73def39818e6edf82cefcf0f554d43bbd262738da82ce037bb687f4`.
- Decompression wrapper: `ev_44e28c18753c0dad74be855ee592003b67d01f4f63b1cda75283a6258ef2e8f5`.
- Incoming order/state: `ev_474369a9f3f966f86b4b6d795b994fc1ab85abd91c1d5e89ed3caf9613e3096d`.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
