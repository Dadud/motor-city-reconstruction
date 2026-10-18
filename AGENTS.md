# Reconstruction evidence workflow

For shipped-binary analysis, follow the installed `reverse-engineer-anything` skill from https://github.com/morluto/rea and [the project workflow](docs/recovery/rea-workflow.md). Ordinary authored-source edits and tests use normal repository tools.

- Use REA as the primary static-analysis source. Reuse compatible retained Evidence/snapshots before producing equivalent analysis. Follow the actual connected tool schemas, not capabilities assumed from upstream main.
- Check CLI, skill and connected-server identities after setup/version changes. A package update does not reload a running MCP server. Use the matching CLI while reconnection is pending; do not label an old connection current.
- Pin the original target SHA-256, provider/version and analysis-profile digest. Do not bypass rejected snapshot/Evidence integrity checks or overwrite old research to make it load.
- Read normalized results and selected retained views. Keep complete original Evidence private under ignored `evidence/`; publish IDs, provenance, limitations and bounded conclusions. Avoid dumping large catalogs/dossiers into conversation.
- Use complete function-body AddressSets and REA references/instruction facts for ownership and absence claims. Never turn `body_bytes` into a presumed contiguous owned extent. Linear Capstone scans are secondary byte-window heuristics only.
- Label static observations, inferences, unknowns and dynamic checks separately. Capstone output is not REA Evidence. Unicorn comparisons execute original instructions under declared synthetic state/bridges; they do not establish live Windows APIs, hardware, networking or a complete game.
- Keep unresolved interfaces and evidence gaps explicit. Use REA unknown/verification facilities when supported by the active session; finite claims and selected traces never prove whole-game equivalence.
- Reuse one matching native session for related questions. Export needed Evidence/snapshots before closing; do not repeatedly reopen or bulk-decompile the installation without a concrete gap.
