# Kusto Terminal

A terminal-style Azure Data Explorer (Kusto) client, built with .NET 8 and Terminal.Gui.

## Prerequisites

- Azure CLI (`az login` command)

## Installation

1. Clone the repository
2. Build the solution:
   ```bash
   dotnet build
   ```
3. Run the application:
   ```bash
   dotnet run --project src/KustoTerminal.CLI
   ```

## Recall the last execution

Place the cursor in a query and press `F8` to restore its latest successful
result for the active cluster and database. Kusto Terminal loads the result
table and execution metadata from the local cache without sending a request to
Kusto or changing any text in the query editor.

Cached executions are stored under `~/.kusto-terminal/history`, retained for 30
days, and limited to the newest 1,000 entries. Query results can contain
sensitive data, so protect this directory like any other local data export.
## Managed shell integration (Windows only)

An optional fixed-target mode accepts credentials from a parent process rather than
performing login:

```text
KustoTerminal --shell-managed --cluster https://cluster.example --database database --tenant opaque-tenant --shell-pipe kt-11111111-2222-3333-4444-555555555555 --shell-parent-pid 123
```

All six arguments are required in managed mode; other/duplicate arguments are
rejected. The cluster must be an exact HTTPS origin (an optional trailing slash
is retained). The tenant is an opaque parent-shell context, not an instruction
to perform local login. The parent must already be listening on its local
`kt-<GUID>` Windows named pipe. The client connects **before UI initialization**,
checks `GetNamedPipeServerProcessId` against the supplied PID, and authenticates
before opening the UI. The parent should restrict pipe access and verify its
launched child's PID.

Protocol v1 uses UTF-8 JSON with a four-byte little-endian byte-count prefix:
requests are at most 4096 bytes, responses at most 65536 bytes. Property names
are case-sensitive. Unknown, duplicate and missing response fields are rejected.

* Request: `Version: 1`, a fresh printable-ASCII `RequestId` (1–64 characters),
  and `ClusterUri` equal to the supplied origin.
* Response: `Version: 1`, matching `RequestId`, integer `Scheme` (`0` = MSAL,
  `1` = dSTS), `AccessToken`, ISO8601 `ExpiresOn` with an explicit offset or `Z`,
  and `ErrorCode: ""`.
* Authentication failure: `ErrorCode: "authentication-failed"`, empty token,
  and default expiry. All error responses close the channel.

Tokens must be nonempty, contain no whitespace/control characters, and expire
more than two minutes in the future. MSAL credentials use the SDK's AAD user-token
mode; dSTS credentials use its dSTS user-token mode. Acquisitions are serialized
and bounded to five minutes, including time waiting for another acquisition.
Each operation requests credentials again, allowing the parent to renew them.
Acquisition cancellation, EOF, invalid frames, peer mismatch and disposal fail closed.
There is no login fallback or reconnect to another parent.

The cluster/database are fixed for tabs, queries, schema and cancellation.
Connection creation/edit/delete and `#connect` are disabled; the connection tree
shows only the supplied target. No saved connections, settings, query/result
history, schema-cache files, user configuration or FPS logs are loaded/written
in managed mode. Explicit user actions such as result export remain available.
Ordinary standalone startup is unchanged. Linux managed startup is rejected.

The source capability marker is
`ManagedShellOptions.Capability = "fixed-target-managed-shell-v1"` in
`src/KustoTerminal.Core/Services/ManagedShellOptions.cs`. This is a feature marker,
not redistribution, signing or platform acceptance approval.

Portable checks (existing dependencies only, .NET 8):

```sh
dotnet build KustoTerminal.sln
dotnet run --project tests/ManagedShell.Tests
python3 tests/ManagedShell.Tests/check-isolation.py
dotnet run --project tests/ManagedShell.Tests --no-build -- --emit-protocol-fixtures
```

The last command emits a JSON map of Base64-encoded complete wire frames, based
on public synthetic vectors in `tests/ManagedShell.Tests/wire-fixtures.json`.
Other implementations can decode these fixtures to check framing, casing,
numeric schemes and both ISO8601 offset forms. Tokens and target are synthetic.
The executable tests exercise the production channel over fragmented streams,
renewal, rejection cases, SDK builders, fixed-target UI wiring and memory-only
state. They do not prove native Windows pipe PID binding, live authentication,
signed deployment or SAW acceptance; those require Windows integration testing.
