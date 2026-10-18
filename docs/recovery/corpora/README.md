# Regression corpus storage

`wave0/index.json` is the authoritative snapshot manifest. It retains corpus
metadata and maps routine cells and connected lifecycle probes to SHA-256 named
`.json.gz` records. The digest covers the uncompressed record, including its
target identity, collection and identifier. Readers verify digests and identities
before using observations. The manifest itself is reviewed/versioned by Git;
these checks detect damage, not an attacker replacing the entire repository.

Current corpus files total approximately 7.4 MB, replacing a 546 MB Git LFS JSON
file. Ordinary Git carries these small compressed files; current checkouts do
not require Git LFS. Historical commits containing `wave0.json` still require
LFS to materialize that historical file. History and old evidence are preserved.

## Use and update

The existing commands use shards automatically:

```sh
python -m tools.run_cell_comparisons build/native
python -m tools.native_counter_mod4_compare build/native/mco_counter_mod4_compare
python -m tools.w0_cell_corpus /path/to/original/mcity.exe
```

The original-execution exporter defaults to updating the shard snapshot. New
records are compressed deterministically and written atomically; the manifest
is replaced last. Unchanged records retain their files. Unreferenced old records
are retained so a reader holding the previous manifest can finish safely. Before
committing, review the manifest and any added records; do not delete old records
while readers may be active. No automatic garbage collection runs.

To migrate a legacy JSON, gzip, or older shard snapshot:

```sh
python -m tools.cell_corpus --corpus /path/to/legacy.json --shard-to /path/to/shards
```

Readers still accept legacy `.json`, `.json.gz`, and schema-1 uncompressed cell
shards. Schema-2 snapshots support cells and probes together. Individual drivers
read only their selected record; the aggregate suite reads one full snapshot.
No fallback to the old corpus or implicit cache can hide missing/corrupt records.

## Migration verification (2026-10-18)

All top-level metadata and canonical hashes of every cell and probe were
compared against the previous JSON. The data remains synthetic original-instruction
observations under declared bridges, not proof of live Windows/game equivalence.
See [throughput research](../throughput-research.md) for measurements and tool priorities.
