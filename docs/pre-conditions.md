# Workshop Pre-Conditions (Unit 0)

> Hard gate. Every TBD below must resolve to a concrete value (or an explicit
> "descoped/deferred to X" line — never blank) before the workshop ships.
> Once resolved, commit the change. The dry-run (Unit 9) re-reads this file
> and fails if any TBD remains for blocking items.

Plan: `docs/plans/2026-05-11-001-feat-tethysdash-mcp-workshop-orchestration-plan.md`
(in the workspace `firoh/` parent — not in this repo).

---

## Q3 — Demo data sensitivity sign-off

**Status:** TBD

**What's needed:** Named data steward confirms the demo dataset committed (or
expected to be committed) to `Aquaveo/nrds_mcps` contains no PII, no embargoed
research data, and no security-sensitive geospatial coordinates.

**How to fill in:**
- Data steward name: `TBD`
- Date confirmed: `TBD` (YYYY-MM-DD)
- Decision: `TBD` (one of: `approved — dataset is public-safe` /
  `descoped — workshop runs against nrds_mcps built-in demo sources only` /
  `deferred — Q3 sign-off captured post-event, workshop ships with built-in sources`)
- Reference: optional Slack/email link

**Blocking?** Soft. If deferred, Unit 6 answer branches must avoid any
nrds_mcps tools that depend on committed fixture data; the workshop runs
against the built-in demo sources.

---

## Q6 — Shared LLM fallback proxy strategy

**Status:** **CLOSED** — Descoped per origin D9.

**Decision:** No Aquaveo-hosted proxy. BYO key (D5) is the only path.
In-session recovery = participant-driven provider switching in the chatbox
LLM Provider Panel (PD5: Anthropic / OpenAI / Ollama Cloud backups
documented in README + pre-workshop email).

No action required.

---

## Q7 — TethysDash SHA pin (`TETHYSDASH_SHA`)

**Status:** TBD

**What's needed:** Known-good commit SHA on `Aquaveo/tethysapp-tethys_dash`,
on the `feature/tethysdash-mcp-server` branch (or `main` if rebased by event
time). Maintainer-validated to pass `pytest tethysapp/tethysdash/tests/mcp/`
(the build-time gate in the devcontainer Dockerfile).

**How to fill in:**
- `TETHYSDASH_SHA`: `TBD` (40-char SHA, no `v` prefix)
- URL: `https://github.com/Aquaveo/tethysapp-tethys_dash/commit/<sha>`
- Date pinned: `TBD` (YYYY-MM-DD)
- Reason for choosing this SHA: `TBD` (e.g., "passes mcp test suite + latest
  D8 chatbox MCP URL panel UX")

**Blocking?** **Hard.** `scripts/setup.sh` reads this from `.env`; Unit 8's
ghcr.io publish workflow checks out this SHA. Workshop cannot run without it.

---

## Q7b — nrds_mcps SHA pin (`NRDS_MCPS_SHA`) — added in pass-1 plan review

**Status:** TBD

**What's needed:** Known-good commit SHA on `Aquaveo/nrds_mcps`. Maintainer-
validated to boot cleanly and expose `/health` + the `streamable-http`
transport. Answer branches (`step-N-answer`) branch from this SHA.

**How to fill in:**
- `NRDS_MCPS_SHA`: `TBD` (40-char SHA, no `v` prefix)
- URL: `https://github.com/Aquaveo/nrds_mcps/commit/<sha>`
- Date pinned: `TBD` (YYYY-MM-DD)
- Reason for choosing this SHA: `TBD`

**Blocking?** **Hard.** `scripts/setup.sh` reads this from `.env`.

---

## Q8 — NSF ACCESS VM resource confirmation

**Status:** TBD

**What's needed:** Confirmed VM size class (cores, RAM, disk) from the ACCESS
allocation. Drives the SC1 budget: <4 cores or <8GB RAM forces the ghcr.io
primary path to be **mandatory** (build-from-source fallback exceeds 20 min
on weaker VMs).

**How to fill in:**
- Cores: `TBD`
- RAM (GB): `TBD`
- Disk (GB): `TBD`
- Docker version available: `TBD`
- Rootless or rootful Docker: `TBD`
- Allocation reference URL or coordinator email: `TBD`
- Egress reachability to `ghcr.io`: `TBD` (some HPC networks block registries;
  if blocked, the ghcr.io image must be pre-pulled or sideloaded)

**Blocking?** **Hard.** If egress to ghcr.io is blocked and the cluster
can't side-load the image, the workshop cannot proceed.

---

## Q10 — TethysDash ChatSidebar MCP URL persistence pre-check
(Added in pass-1 plan review.)

**Status:** TBD

**What's needed:** Confirm that the `ChatSidebar` in TethysDash at
`TETHYSDASH_SHA` persists user-added MCP server URLs to browser localStorage
with a stable key. If yes, the workshop's segment-2 "add MCP URL" step happens
once per participant per workshop. If no, document the manual re-add step as
expected behavior (not a known bug).

**How to fill in:**
- Persistence confirmed at SHA: `TBD` (yes / no)
- localStorage key (if yes): `TBD`
- Behavior on browser refresh: `TBD` (URL retained / URL lost)
- Behavior on `docker compose restart tethysdash`: `TBD` (URL retained / URL lost)

**Blocking?** Soft. Workshop runs either way; the README troubleshooting
section adjusts based on the answer.

---

## Q11 — TethysDash healthcheck path pre-flight
(Added in pass-1 plan review.)

**Status:** TBD

**What's needed:** Confirm the static-asset path used as the compose
healthcheck returns 200 unauthenticated under the TethysDash dev settings
that `init.sh` applies. Default proposed path:
`/static/tethys_apps/css/tethys_app_base.css`. Pre-flight by running
`tethys manage start -p 8000` locally (or against a freshly built workshop
image) and curling the path.

**How to fill in:**
- Path verified: `TBD` (yes / no)
- If no — alternative path used: `TBD`
- HTTP response: `TBD` (e.g., `200 OK` or `302 → /accounts/login`)
- Verified at TETHYSDASH_SHA: `TBD`

**Blocking?** Soft-to-hard. If no static path returns 200, the healthcheck
must use a different strategy (e.g., a Tethys admin API endpoint, or accept
3xx). Workshop runs but `docker compose up -d` reports never-healthy.

---

## How dry-run (Unit 9) uses this file

Unit 9's checklist verifies every entry above is non-TBD before the
"workshop-ready" sign-off. Soft-blocking items may carry an explicit
"descoped/deferred" status; hard-blocking items (Q7, Q7b, Q8) must have
concrete values.

## Change log

- 2026-05-11 — File created (Unit 0 scaffolding, pass-1 plan review baseline).
