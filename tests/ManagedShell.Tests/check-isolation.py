"""Run built portable tests and Linux startup checks with monitored application-state paths."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[2]
state = root / "tests/ManagedShell.Tests/isolation-state"
if state.exists():
    raise RuntimeError("Remove the previous isolation-state fixture before running this test.")
state.mkdir()
try:
    for relative in [
        ".config/KustoTerminal/connections.json",
        ".config/KustoTerminal/user-settings.json",
        ".kusto-terminal/cache/schema.json",
        ".kusto-terminal-fps.log",
        ".tui/config.json",
    ]:
        path = state / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("invalid persisted fixture -- must not be read or changed", encoding="utf-8")

    def snapshot():
        return {str(p.relative_to(state)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in state.rglob("*") if p.is_file()}

    before = snapshot()
    env = dict(os.environ, HOME=str(state), XDG_CONFIG_HOME=str(state / ".config"),
               APPDATA=str(state / ".config"), USERPROFILE=str(state))
    result = subprocess.run(
        ["dotnet", "tests/ManagedShell.Tests/bin/Debug/net8.0/ManagedShell.Tests.dll"],
        cwd=root, env=env, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS:" in result.stdout, result.stdout
    print(result.stdout.strip())
    if os.name != "nt":
        cli = ["dotnet", "src/KustoTerminal.CLI/bin/Debug/net8.0/KustoTerminal.dll"]
        args = ["--shell-managed", "--cluster", "https://example.kusto.windows.net",
                "--database", "db", "--tenant", "opaque", "--shell-pipe",
                "kt-11111111-2222-3333-4444-555555555555", "--shell-parent-pid", "123"]
        for extra in [[], ["--fps"], ["--cluster", "https://other.test"]]:
            result = subprocess.run(cli + args + extra, cwd=root, env=env, text=True,
                                    capture_output=True, timeout=10)
            assert result.returncode != 0 and "Managed shell startup failed" in result.stdout, result
            assert "Starting Terminal UI" not in result.stdout, result.stdout
    assert snapshot() == before, "Managed execution changed application state."
    assert not (root / "tests/ManagedShell.Tests/forbidden-cache").exists(), "Schema cache was created."
    print("PASS: no managed application-state writes; Linux CLI rejects managed startup before UI.")
finally:
    shutil.rmtree(state)
