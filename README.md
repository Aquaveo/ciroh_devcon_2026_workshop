# CIROH DevCon 2026 — TethysDash + MCP Workshop

A 2-hour hands-on workshop that brings up TethysDash plus two MCP servers
(`nrds_mcps` for data-layer tools, `tethysdash_mcps` for visualization-layer
tools) on a per-participant NSF ACCESS VM. Participants edit MCP tool code
mid-session and observe the change in the chatbox.

> **This is a skeleton README.** Full participant guide (prerequisites, SSH
> tunnel, segment walkthrough, troubleshooting) lands in Unit 5 of the plan
> at `docs/plans/2026-05-11-001-feat-tethysdash-mcp-workshop-orchestration-plan.md`
> in the workspace `firoh/` parent.

---

## Status

This repo is **under construction** for the 2026 Summit. Tracking:

**Plan 001** — initial two-service workshop orchestration:

- [x] Unit 0 — Pre-conditions placeholder (`docs/pre-conditions.md`)
- [x] Unit 1 — Repo scaffolding (devcontainer, `.gitignore`, `.env.example`, README skeleton)
- [x] Unit 2 — Scripts (`setup.sh`, `reset-repos.sh`, `tunnel.sh`, `restart-mcp.sh`)
- [x] Unit 3 — `docker-compose.yml` (tethysdash service + nrds_mcps stub)
- [x] Unit 4 — `nrds_mcps` service: source bind-mount overlay + `/health` healthcheck + `user: root` override
- [ ] Unit 5 — Full README + pre-workshop email template
- [ ] Unit 6 — Answer branches on `Aquaveo/nrds_mcps` (maintainer-owned)
- [ ] Unit 7 — DESCOPED per origin D9 (BYO LLM key only; no shared proxy)
- [ ] Unit 8 — GitHub Actions: `publish-image.yml` (workshop tethysdash image)
- [ ] Unit 9 — Dry-run on NSF ACCESS VM (hard ship gate)

**Plan 008** — third-service integration (`tethysdash_mcps` visualization layer):

- [x] Unit 1 — `tethysdash_mcps` compose service (image + bind-mount overlay + healthcheck)
- [x] Unit 2 — `.env.example` + `pre-conditions.md` (`TETHYSDASH_MCPS_SHA`, `TETHYSDASH_MCPS_IMAGE_TAG`, Q7d, Q7 extension)
- [x] Unit 3 — `setup.sh` third-repo clone
- [x] Unit 4 — Operational scripts generalized for two MCP services
- [x] Unit 5 — README documents two-MCP-server configuration
- [ ] Unit 6 — Dry-run on NSF ACCESS VM with three services

**Plan 2026-05-12-001** — MCP servers run with `fastmcp` hot-reload:

- [x] Unit 1 — `scripts/run-mcp-with-reload.py` launcher + compose `entrypoint:` + `command:` overrides on both MCP services
- [x] Unit 2 — Polling-fallback troubleshooting note in README
- [x] Unit 3 — README quick-start leads with hot-reload, `restart-mcp.sh` demoted to troubleshooting

See pre-conditions: [`docs/pre-conditions.md`](docs/pre-conditions.md).

## VM provisioning (one-time per VM)

code-server runs **on the VM**, not in compose, so its integrated terminal
is the VM shell (you can run `docker compose logs`, `bash scripts/...`,
etc. directly from inside the IDE). Install it once per VM:

```bash
git clone https://github.com/Aquaveo/ciroh_devcon_2026_workshop.git ~/workshops/devcon
cd ~/workshops/devcon
bash scripts/install-code-server.sh
```

The script wraps the official install + systemd-enable from
https://github.com/coder/code-server. It's idempotent; re-running it is
a no-op if code-server is already present. The script prints the
auto-generated password from `~/.config/code-server/config.yaml` at the
end — copy it; you'll paste it into the browser after the tunnel is up.

## Quick start (preview — full version in Unit 5)

On the NSF ACCESS VM, **after VM provisioning above**:

```bash
# 1. Open this repo in code-server (http://localhost:8080 via the tunnel
#    below), OR work in an SSH session — both paths work identically.
# 2. Copy .env.example to .env:
cp .env.example .env

# 3. After setup.sh completes, bring the stack up:
docker compose up -d

# 4. From your laptop, open the SSH tunnel (forwards four ports: 8000, 8080, 9000, 9001):
bash scripts/tunnel.sh           # prints the command; copy-paste in another terminal

# 5. In your laptop browser, open the two URLs:
#       http://localhost:8000    # TethysDash UI
#       http://localhost:8080    # code-server (browser VS Code)
#                                #   paste the password from install-code-server.sh

# 6. In TethysDash's chatbox sidebar (gear icon → MCP servers), add BOTH:
#       http://localhost:9000/mcp    # nrds_mcps  (data-layer tools)
#       http://localhost:9001/mcp    # tethysdash_mcps  (visualization-layer tools)
#    Both URLs persist in localStorage per dashboard; you only set them once.

# 7. In code-server, edit any MCP tool source file and save (Ctrl+S):
#       repos/nrds_mcps/nextgen_mcp/tools/<some_tool>.py     # or
#       repos/tethysdash_mcps/tethysdash_mcp/<some_module>.py
#    The server auto-restarts in ~1-2 seconds (watchfiles + inotify on the
#    bind-mount). Then refresh the TethysDash tab to force chatbox-core
#    to re-probe the tool catalog.
```

## Edit loop

Both MCP servers run under a `fastmcp`-based hot-reload wrapper
(`scripts/run-mcp-with-reload.py`). Participants edit via **code-server**
in the browser (`http://localhost:8080` via the SSH tunnel) — no SSH +
vim required. The loop:

| Step | Action |
|------|--------|
| 1 | In the code-server tab (`http://localhost:8080`), navigate to `repos/nrds_mcps/nextgen_mcp/` or `repos/tethysdash_mcps/tethysdash_mcp/` and edit a file. |
| 2 | Save (Ctrl+S / Cmd+S). The host-side bind-mount surfaces the change to the MCP container; `watchfiles` detects it and respawns the FastMCP process within 1–2 seconds. |
| 3 | Switch to the TethysDash tab (`http://localhost:8000`) and refresh. The chatbox re-probes the MCP server and picks up the change (renamed tools, changed schemas, modified return envelopes). |

If your edit introduces an import-time syntax error, the server will
crash on respawn. The fix is the same: re-edit the file and save again
— the watcher is still alive and will retry. Use
`docker compose logs --tail=30 nrds_mcps` (or `tethysdash_mcps`) to see
the traceback while diagnosing.

## Repository layout

```
.
├── .devcontainer/        Workshop control-plane devcontainer (host Docker socket).
├── .env.example          Template for per-participant .env (SHAs, image tags).
├── .gitignore            Ignores repos/, .env, logs.
├── README.md             This file (skeleton; full guide in Unit 5).
├── docs/
│   └── pre-conditions.md Unit 0 gate (SHAs, data steward, VM specs).
├── scripts/
│   ├── install-code-server.sh  ONE-TIME per-VM install of code-server (host-side, not compose).
│   ├── setup.sh                Clone the three consumed repos, pull workshop image.
│   ├── reset-repos.sh          WIP-protected recovery (refuses without --force).
│   ├── tunnel.sh               Prints the SSH -L command (forwards 4 ports).
│   ├── restart-mcp.sh          docker compose restart <service> + health poll (escape hatch).
│   └── run-mcp-with-reload.py  fastmcp hot-reload wrapper run inside each MCP container.
└── repos/                Gitignored. Populated by setup.sh:
    ├── tethysapp-tethys_dash/   @ TETHYSDASH_SHA
    ├── nrds_mcps/               @ NRDS_MCPS_SHA
    └── tethysdash_mcps/         @ TETHYSDASH_MCPS_SHA
```

## Architecture (one-liner)

Browser on participant laptop → SSH tunnel → NSF ACCESS VM → three compose
services (TethysDash on `:8000`, nrds_mcps on `:9000`, tethysdash_mcps on
`:9001`). The chatbox is configured with **two MCP server URLs**:

- `http://localhost:9000/mcp` — **`nrds_mcps`**, data-layer tools (intake
  plugins, time-series fetch, NRDS-specific sources).
- `http://localhost:9001/mcp` — **`tethysdash_mcps`**, visualization-layer
  tools (Plotly, cards, tables, maps, 12 map-layer add tools, RFC 6902
  patches on existing tiles).

Browser → MCP traffic goes through the SSH tunnel, NOT through compose-
internal DNS. The one compose-internal HTTP edge is `tethysdash_mcps →
tethysdash` for two backend-touching tools (`list_intake_plugins`,
`add_dynamic_map_layer`) — they resolve `http://tethysdash:8000/apps/tethysdash`
on the docker network. Sources for both MCP servers are bind-mounted into
their respective published images (`ghcr.io/aquaveo/nrds-mcps:<tag>`,
`ghcr.io/aquaveo/tethysdash-mcps:<tag>`) so participant edits override the
baked-in copies; `bash scripts/restart-mcp.sh <service>` picks them up.

## Known caveats

- **`register_runtime_plugin` slash-command returns `registration_not_supported`.**
  The standalone `tethysdash_mcps` server has no authenticated write path,
  so this tool is feature-flagged off. Plugin registration goes through the
  **chatbox sidebar's plugin-registration UI** (which posts to tethysdash's
  `/runtime-plugins/sync/` with the user's session). The standalone reads
  the resulting registry over HTTP on its next tool call — no restart
  needed.
- **Tool list cached by chatbox-core.** After an MCP server auto-restart
  (or a manual `restart-mcp.sh`), the chatbox may show a stale tool list
  until the next probe interval. Refreshing the browser tab forces a
  re-probe.
- **No CORS / auth on either MCP server.** Per-VM isolation + 127.0.0.1
  binding + SSH tunnel are the security boundary. Do NOT expose either
  port to a non-loopback network.

## Troubleshooting

### Hot-reload didn't fire after I saved a file

In rare cases, the participant VM's storage driver doesn't propagate
inotify events through Docker bind-mounts. Symptom: editing
`repos/nrds_mcps/nextgen_mcp/<file>.py` and saving produces no
"reload"/"detected changes" log line in `docker compose logs nrds_mcps`,
and the tool behavior doesn't update.

Quick check:
```bash
docker compose logs -f nrds_mcps &
sleep 1; touch repos/nrds_mcps/nextgen_mcp/__init__.py; sleep 4
kill %1 2>/dev/null
# Expect: a "watching" / "reload" / "detected" line in the captured output.
```

If no event fires, add the polling fallback to the affected service in
`docker-compose.yml`:

```yaml
nrds_mcps:
  environment:
    WATCHFILES_FORCE_POLLING: "true"
```

Then `docker compose up -d nrds_mcps` to re-apply. Polling burns a small
amount of idle CPU (still fine on the workshop VM SKU); inotify is the
default specifically because it avoids that cost.

### Manual restart fallback

If a container is wedged (process running but unresponsive, healthcheck
stuck unhealthy, hot-reload not respawning after an import crash), use
the manual restart script as an escape hatch:

```bash
bash scripts/restart-mcp.sh nrds_mcps          # or
bash scripts/restart-mcp.sh tethysdash_mcps
```

It runs `docker compose restart <service>` and polls the healthcheck
until healthy, printing the last 20 log lines on success or 50 on
failure. The hot-reload watcher restarts automatically with the
container, so you keep the auto-restart-on-save behavior afterward.

### Stale UI after a tethysapp-tethys_dash edit

Editing `repos/tethysapp-tethys_dash/reactapp/...` will NOT show up in
the running app: the workshop image ships the committed React bundle as
a static artifact and the devcontainer has no Node/webpack to rebuild
it. See
[`docs/solutions/best-practices/tethysdash-bundle-shipped-via-copy-2026-05-11.md`](../../docs/solutions/best-practices/tethysdash-bundle-shipped-via-copy-2026-05-11.md)
in the workspace for the full mechanism. The workshop's pedagogical
focus is MCP-tool editing (which IS hot-reloadable); React editing
needs an out-of-band `npm run build` + bundle commit, which is
intentionally out of scope here.

## License

MIT. (Workshop content + scripts. The consumed repos have their own licenses.)
