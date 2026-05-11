# CIROH DevCon 2026 — TethysDash + MCP Workshop

A 2-hour hands-on workshop that brings up TethysDash + the `nrds_mcps` MCP
server on a per-participant NSF ACCESS VM. Participants edit MCP tool code
mid-session and observe the change in the chatbox.

> **This is a skeleton README.** Full participant guide (prerequisites, SSH
> tunnel, segment walkthrough, troubleshooting) lands in Unit 5 of the plan
> at `docs/plans/2026-05-11-001-feat-tethysdash-mcp-workshop-orchestration-plan.md`
> in the workspace `firoh/` parent.

---

## Status

This repo is **under construction** for the 2026 Summit. Tracking:

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

# 4. From your laptop, open the SSH tunnel:
bash scripts/tunnel.sh           # prints the command; copy-paste in another terminal

# 5. In your laptop browser, open http://localhost:8000 and follow the
#    workshop README from there.
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
    └── nrds_mcps/               @ NRDS_MCPS_SHA
```

## Architecture (one-liner)

Browser on participant laptop → SSH tunnel → NSF ACCESS VM → two compose
services (TethysDash on `:8000`, nrds_mcps on `:9000`). Chatbox calls
`http://localhost:9000/mcp` through the tunnel, NOT through compose-internal
DNS. Source for nrds_mcps is bind-mounted from `repos/nrds_mcps/nextgen_mcp`
into the published `ghcr.io/aquaveo/nrds-mcps:<tag>` image so participant
edits override the baked-in copy and a `docker compose restart nrds_mcps`
picks them up.

## License

MIT. (Workshop content + scripts. The consumed repos have their own licenses.)
