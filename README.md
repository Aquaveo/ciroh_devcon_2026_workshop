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

See pre-conditions: [`docs/pre-conditions.md`](docs/pre-conditions.md).

## Quick start (preview — full version in Unit 5)

On the NSF ACCESS VM:

```bash
# 1. Open this repo in DevPod (or VS Code Remote-Containers). The workshop
#    devcontainer's postCreateCommand runs scripts/setup.sh.
# 2. Copy .env.example to .env and fill in the SHAs published in the
#    pre-workshop email.
cp .env.example .env

# 3. After setup.sh completes, bring the stack up:
docker compose up -d

# 4. From your laptop, open the SSH tunnel (forwards three ports: 8000, 9000, 9001):
bash scripts/tunnel.sh           # prints the command; copy-paste in another terminal

# 5. In your laptop browser, open http://localhost:8000.

# 6. Open the chatbox sidebar (gear icon → MCP servers) and add BOTH URLs:
#       http://localhost:9000/mcp    # nrds_mcps  (data-layer tools)
#       http://localhost:9001/mcp    # tethysdash_mcps  (visualization-layer tools)
#    Both URLs persist in localStorage per dashboard; you only set them once.
```

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
│   ├── setup.sh          Clone tethysapp-tethys_dash + nrds_mcps, pin SHAs, pull image.
│   ├── reset-repos.sh    WIP-protected recovery (refuses without --force).
│   ├── tunnel.sh         Prints the SSH -L command.
│   └── restart-mcp.sh    docker compose restart nrds_mcps + health poll.
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
- **Tool list cached by chatbox-core.** After `restart-mcp.sh tethysdash_mcps`
  or `restart-mcp.sh nrds_mcps`, the chatbox may show a stale tool list
  until the next probe interval. Refreshing the browser tab forces a
  re-probe.
- **No CORS / auth on either MCP server.** Per-VM isolation + 127.0.0.1
  binding + SSH tunnel are the security boundary. Do NOT expose either
  port to a non-loopback network.

## License

MIT. (Workshop content + scripts. The consumed repos have their own licenses.)
