# Local fan-server tester

Double-click `test-fan-server.cmd` in the repository on Windows, or run
`python -m tools.fan_server_test` from the repository root. The Windows launcher
uses the project's `.venv` when available and otherwise uses `python` on PATH.
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
The GUI also runs the recovered race-entry construction probe after login;
this validates local task ordering and installed patch settings but does not join a race.

**Cancel** requests cancellation between operations. An operation already waiting
on the network may need to reach its timeout before the worker stops. Closing the
window also requests cancellation. A new test cannot start until the previous
worker finishes. Passwords must be entered again for each test.

Only fixed stage labels, booleans and counts from the safe result are shown.
Detailed exception messages, authentication URLs, tickets, passwords and account
object representations are withheld. Persona names are shown only for your local
selection. This is a protocol/data-access test; successful results do not establish
race compatibility, complete garage behavior or server-version equivalence.

Development checks use synthetic mocks without an account. No live account test
is implied by shipping this interface.

## Command-line check

From an interactive terminal in the repository:

    python -m tools.fan_server_check "C:/Program Files (x86)/EA Games/Motor City Online" --shard-id 44 --source nps/shardlistip.ini --login --fetch-garage

Add `--probe-race-entry` to include the recovered race-entry construction probe
in the safe JSON report after login.

On Windows you can use the same flags through `test-fan-server-live.cmd`.

Use --persona-id when you already know the persona. Add --catalogue when Online.mdb is installed.
Preflight without --login validates discovery, certificate pin and external identity only.
