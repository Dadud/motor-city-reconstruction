# Local fan-server tester

First time only, double-click `setup-fan-server-test.cmd` to create the venv and install networking dependencies. Then double-click `test-fan-server.cmd` in the repository on Windows, or run
`python -m tools.fan_server_test` from the repository root. The Windows launcher
requires the project's `.venv`; run the setup launcher if it is missing.
For a command-line live login with garage fetch on the installed MotorCity Revival
shard, double-click `test-fan-server-live.cmd` (edit `MCO_DATA` inside if your
install path differs).
Linux needs Python with Tk support (often provided by the distribution's
`python3-tk` package), the project dependencies and a desktop display.

Select your original installation folder. The default Windows location is
`C:\Program Files (x86)\EA Games\Motor City Online`. Enter your fan-server account
name and password and press **Test connection**. The password stays hidden and
is cleared from its entry as the test begins. No credentials or account payloads
are logged or written to disk by this window.

The tester uses the installed fan-server configuration through
`client.fanserver_test.run_test`. It checks authorization, binary account login,
personas, lobby/primary connections and persona garage data. If persona selection
is needed, choose the desired name in the window and press **Continue**. The
window stays responsive while the network worker runs.
The GUI tests live connection and garage-data requests only. Catalogue enrichment
and local race-entry probes are optional command-line research checks. They are
excluded from the default test so a local research check cannot be confused with
a successful live race. The tester does not start the native driving client.

**Cancel** requests cancellation between operations. An operation already waiting
on the network may need to reach its timeout before the worker stops. Closing the
window also requests cancellation. A new test cannot start until the previous
worker finishes. Passwords must be entered again for each test.

Only fixed stage labels, booleans and counts from the safe result are shown.
Detailed exception messages, authentication URLs, tickets, passwords and account
object representations are withheld. Persona names are shown only for your local
selection. This is a protocol/data-access test; successful results do not establish
race compatibility, complete garage behavior or server-version equivalence.

On failure, the window shows the last attempted stage and a fixed error category:
authorization denied, setup failed, timeout, connection failed, network/file error,
or protocol/data error. **Save test report…** exports only fixed status fields and
counts. It excludes account names, persona names/IDs, server addresses and private
exception details. Share that report when diagnosing an incompatibility. A failed
report does not claim that earlier stages passed unless a result records them.

Development checks use synthetic mocks without an account. No live account test
is implied by shipping this interface.

## Command-line check

From an interactive terminal in the repository:

    python -m tools.fan_server_check "C:/Program Files (x86)/EA Games/Motor City Online" --shard-id 44 --source nps/shardlistip.ini --login --fetch-garage

Add `--probe-race-entry` to include the race-entry recovery-gap report after
login. It reports missing task ordering and authenticated arguments; it does not
construct or execute a race-entry sequence.

On Windows you can use the same flags through `test-fan-server-live.cmd`.
When launched from a terminal, append options such as
`--persona-id 123 --report fan-server-test-report.json`. The launcher retains
the check's exit status after its pause. `MCO_DATA` can also be set in the
launching terminal to override the default installation folder.

`--report PATH` saves a shareable JSON file on success or failure, including
preflight failures. It contains fixed stage/category labels, booleans and counts,
with no account names, persona IDs, server addresses or private exception text.
Choose a writable destination; this option replaces any report at that path.
The terminal's ordinary JSON includes local shard and persona identifiers, so
share the exported report when asking for help.

Use --persona-id when you already know the persona. Add --catalogue when Online.mdb is installed.
Preflight without --login validates discovery, certificate pin and external identity only.

## What success looks like

**Preflight only** (no account): JSON shows `preflight_passed: true`, shard **MotorCity Revival** (ID **44**).

**Live test** (with your fan-server account):

| Field | Meaning |
| --- | --- |
| `success` | Entire flow completed without a blocking error |
| `account_authenticated` | Binary account login succeeded |
| `lobby_connected` | Lobby channel connected |
| `primary_connected` | Primary MCOTS channel connected |
| `garage_loaded` | Persona garage records received (when garage fetch is enabled) |
| `persona_count` / `garage_record_count` | Non-zero counts mean data came back from the server |
| `race_entry_probe_passed` / `room_channel_probe_passed` | Currently false: race/room entry remains incomplete |
| `missing_task_order` / `missing_authenticated_arguments` | Outstanding recovery work (with `--probe-race-entry`) |
| `protocol_selection_unverified` | Patch settings have not been proved to select a particular channel protocol |
| `positional_updates_hz` | Declared installed patch rate (often **32**); does not prove actual network timing |
| `last_stage` | Final stage label; `complete` on success |

Race-entry and room-channel probes **do not join a race**. They report research
gaps and observed patch settings. Dispatcher task kinds alone do not establish
the original runtime sequence, complete room arguments or server compatibility.

If something fails, note `last_stage` and which booleans stayed false. Credentials are never included in the JSON output.
The command-line check returns a nonzero exit status for failed or cancelled live
tests. Error JSON includes `failure_code` and `last_stage` when the flow fails.
The GUI and terminal provide fixed next-step guidance. For authorization denial,
check the account in the original client; for connection/timeout failures, compare
server reachability from the same computer. Protocol/data failures may be
reconstruction incompatibilities: save the failed-stage report for investigation.

## Current local verification

On Windows, the installed configuration passes unauthenticated preflight for
MotorCity Revival shard 44. The tester window initializes and displays a failed
stage with report export enabled. The complete Python suite passes 546 tests,
including stage retention, credential exclusion and failure exit-status checks.
These checks do not constitute an authenticated account run. Your private local
account test is still needed; server version remains unreported.

