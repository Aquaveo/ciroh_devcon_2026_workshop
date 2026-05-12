#!/usr/bin/env python3
"""
run-mcp-with-reload.py — workshop hot-reload wrapper for MCP servers.

Wraps a `python -m <pkg>.mcp_server` invocation in FastMCP's watchfiles-
based reload loop. The compose `command:` for each MCP service invokes
this launcher, which:

  1. Spawns the upstream entrypoint (`python -m <module>`) as a subprocess.
  2. Watches `<watch-dir>` for file changes via `watchfiles`.
  3. Kills + respawns the subprocess on any change.

Why not `fastmcp run --reload` directly?
  The FastMCP CLI's `run` command imports the target file at a path, which
  breaks for packages whose entry-point module uses relative imports
  (`from .utils import ...`). The nrds_mcps entry-point at
  /app/nextgen_mcp/mcp_server.py is exactly this case. Using
  `python -m <pkg>.mcp_server` (which sets `__package__` correctly) and
  wrapping it with FastMCP's watcher gives us the same hot-reload UX
  with zero coupling to the entry-point file's import style.

Why use `fastmcp.cli.run.run_with_reload`?
  It IS the same watchfiles-driven restart loop that `fastmcp run --reload`
  uses internally. Bypassing the CLI layer lets us pass an arbitrary
  command list. Documented at
  https://gofastmcp.com/python-sdk/fastmcp-cli-run#run_with_reload.

Usage (inside the container, via compose `command:`):

    python /workshop-scripts/run-mcp-with-reload.py <pkg.module> <watch-dir>

Example (nrds_mcps service):

    python /workshop-scripts/run-mcp-with-reload.py \
        nextgen_mcp.mcp_server \
        /app/nextgen_mcp

Polling fallback:
  If inotify events don't propagate through the bind-mount on a
  particular VM SKU, set `WATCHFILES_FORCE_POLLING=true` in the compose
  env for the affected service. `watchfiles` reads that env var directly;
  no code change needed.

Plan reference:
  docs/plans/2026-05-12-001-feat-workshop-mcp-hot-reload-plan.md
"""

import sys
from pathlib import Path

# Imported lazily-by-position so a missing fastmcp install produces a clear
# error message instead of an opaque ModuleNotFoundError on script load.
try:
    from fastmcp.cli.run import run_with_reload
except ImportError as exc:  # pragma: no cover — environment guard, not logic
    print(
        "FAIL: cannot import fastmcp.cli.run.run_with_reload. "
        "Is the fastmcp package installed in this container?",
        file=sys.stderr,
    )
    print(f"      Underlying error: {exc!r}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: run-mcp-with-reload.py <pkg.module> <watch-dir>",
            file=sys.stderr,
        )
        print(
            "Example: run-mcp-with-reload.py nextgen_mcp.mcp_server "
            "/app/nextgen_mcp",
            file=sys.stderr,
        )
        sys.exit(2)

    module = sys.argv[1]
    watch_dir = Path(sys.argv[2])

    if not watch_dir.is_dir():
        print(
            f"FAIL: watch-dir does not exist or is not a directory: {watch_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # `cmd` is the upstream entrypoint, unchanged. We use the same Python
    # interpreter that's running this launcher (sys.executable) so the
    # subprocess inherits the image's venv unambiguously.
    cmd = [sys.executable, "-m", module]

    print(
        f"[run-mcp-with-reload] watching {watch_dir} → respawning "
        f"`{' '.join(cmd)}` on file changes",
        flush=True,
    )

    run_with_reload(cmd, reload_dirs=[watch_dir])


if __name__ == "__main__":
    main()
