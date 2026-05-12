#!/usr/bin/env bash
#
# setup.sh — workshop bootstrap.
#
# Idempotent. Safe to re-run.
#
# Steps:
#   1. Read pinned SHAs + image tag from .env (fallback: .env.example).
#   2. Clone-or-pull the three consumed repos into ./repos/ and check out the
#      pinned SHAs (detached HEAD). Source remotes are per-repo:
#        tethysplatform/tethysapp-tethys_dash  (canonical upstream)
#        Aquaveo/nrds_mcps
#        Aquaveo/tethysdash_mcps
#   3. Pull ghcr.io/aquaveo/ciroh-devcon-2026:${IMAGE_TAG}; on failure,
#      fall back to docker compose build tethysdash (~10-20 min on weak VMs).
#
# Emits a one-line OK/FAIL summary per step. Exits non-zero on any FAIL.
#
# Plan reference: Unit 2 in
#   docs/plans/2026-05-11-001-feat-tethysdash-mcp-workshop-orchestration-plan.md

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"
cd "${WORKSHOP_ROOT}"

# ---------------------------------------------------------------------------
# 1. Read .env (fallback to .env.example so first-time setup still works).
# ---------------------------------------------------------------------------
if [[ -f .env ]]; then
    ENV_FILE=.env
elif [[ -f .env.example ]]; then
    ENV_FILE=.env.example
    echo "WARN: .env not found; reading defaults from .env.example."
    echo "      Copy .env.example to .env and fill in SHAs before workshop day."
else
    echo "FAIL: neither .env nor .env.example exists in ${WORKSHOP_ROOT}." >&2
    exit 1
fi

# shellcheck source=/dev/null
set -a; . "${ENV_FILE}"; set +a

# Validate required vars are set to non-placeholder values.
require_var() {
    local name="$1"
    local val="${!name:-}"
    if [[ -z "${val}" || "${val}" == "TBD" ]]; then
        echo "FAIL: ${name} is not set (or still 'TBD') in ${ENV_FILE}." >&2
        echo "      Fill it in per docs/pre-conditions.md before re-running." >&2
        return 1
    fi
    return 0
}

# All three SHAs and three image tags are required.
require_var TETHYSDASH_SHA            || exit 1
require_var NRDS_MCPS_SHA             || exit 1
require_var TETHYSDASH_MCPS_SHA       || exit 1
require_var IMAGE_TAG                 || exit 1
require_var NRDS_MCPS_IMAGE_TAG       || exit 1
require_var TETHYSDASH_MCPS_IMAGE_TAG || exit 1

# ---------------------------------------------------------------------------
# 2. Clone-or-pull the two repos. Per-repo strict failure.
# ---------------------------------------------------------------------------
clone_or_pull() {
    local repo_name="$1"        # tethysapp-tethys_dash | nrds_mcps | tethysdash_mcps
    local sha="$2"
    local target="repos/${repo_name}"

    # Per-repo source URL. tethysapp-tethys_dash lives in the canonical
    # tethysplatform org upstream; the two MCP servers are Aquaveo-owned.
    # An unknown repo name is a programming error in setup.sh itself
    # (callers below are an allowlist), so fail loud.
    local url
    case "${repo_name}" in
        tethysapp-tethys_dash) url="https://github.com/tethysplatform/${repo_name}.git" ;;
        nrds_mcps|tethysdash_mcps) url="https://github.com/Aquaveo/${repo_name}.git" ;;
        *)
            echo "FAIL: clone_or_pull called with unknown repo '${repo_name}'." >&2
            return 1
            ;;
    esac

    # Half-clone detection: dir exists but no .git inside → wipe and re-clone.
    if [[ -d "${target}" && ! -d "${target}/.git" ]]; then
        echo "INFO: ${target} exists but has no .git — treating as half-clone, removing."
        rm -rf "${target}"
    fi

    if [[ ! -d "${target}" ]]; then
        echo "INFO: cloning ${url} → ${target}"
        if ! git clone --quiet "${url}" "${target}"; then
            echo "FAIL: git clone ${url} failed." >&2
            return 1
        fi
    else
        echo "INFO: ${target} exists; fetching + ff-only pull on default branch"
        # Pull the default branch first so the SHA we want to check out is
        # guaranteed reachable; ff-only fails loudly if a participant has
        # diverged, which steers them to reset-repos.sh.
        if ! git -C "${target}" fetch --quiet origin; then
            echo "FAIL: git fetch in ${target} failed." >&2
            return 1
        fi
        # Best-effort ff: if we're on a branch and it's ff'able, pull it.
        # If we're on a detached HEAD (typical after a prior setup.sh run),
        # skip the ff-pull and rely on the SHA checkout below.
        local cur_branch
        cur_branch="$(git -C "${target}" symbolic-ref --quiet --short HEAD 2>/dev/null || echo '')"
        if [[ -n "${cur_branch}" ]]; then
            if ! git -C "${target}" pull --ff-only --quiet origin "${cur_branch}"; then
                echo "FAIL: ${target} has diverged from origin/${cur_branch}." >&2
                echo "      Recover with: bash scripts/reset-repos.sh ${repo_name} --force" >&2
                return 1
            fi
        fi
    fi

    # Check out the pinned SHA (produces detached HEAD intentionally).
    if ! git -C "${target}" checkout --quiet "${sha}"; then
        echo "FAIL: git checkout ${sha} in ${target} failed (SHA invalid or unreachable)." >&2
        return 1
    fi

    echo "OK: ${target} @ ${sha}"
    return 0
}

mkdir -p repos

clone_or_pull tethysapp-tethys_dash "${TETHYSDASH_SHA}"       || exit 1
clone_or_pull nrds_mcps             "${NRDS_MCPS_SHA}"        || exit 1
clone_or_pull tethysdash_mcps       "${TETHYSDASH_MCPS_SHA}"  || exit 1

# ---------------------------------------------------------------------------
# Removed 2026-05-12: bundle-presence guard.
#
# The previous version of this section checked that
# tethysapp/tethysdash/public/frontend/main.js existed at TETHYSDASH_SHA
# under the assumption that the devcontainer Dockerfile was Python-only
# and shipped the committed bundle as-is via `COPY . .` (Q7c in
# docs/pre-conditions.md). PR #122 on tethysplatform/tethysapp-tethys_dash
# (commit 29b7bc8, 2026-05-12) replaced that Dockerfile with a multi-
# stage build whose node:20-slim builder stage runs `npm run build` and
# overlays the fresh bundle into the runtime stage. With the new
# Dockerfile, the committed source state of public/frontend/ no longer
# determines what the image serves, so a bundle-presence guard on the
# source tree would produce false positives on SHAs that legitimately
# don't commit a bundle. Q7c is documented as closed; this guard is
# retired.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 3. Pull-or-build the TethysDash workshop image. Compose's `image:` + `build:`
#    semantics: `docker compose up` will only pull if the image is absent
#    AND `pull_policy: always` is unset. We make the pull explicit here so
#    participants don't need to remember it before `docker compose up -d`.
# ---------------------------------------------------------------------------
echo "INFO: pulling ghcr.io/aquaveo/ciroh-devcon-2026:${IMAGE_TAG}"
if docker compose pull tethysdash 2>/dev/null; then
    echo "OK: image ready (pulled ghcr.io/aquaveo/ciroh-devcon-2026:${IMAGE_TAG})"
else
    echo "WARN: image pull failed (image unavailable, no auth, or no network)."
    echo "INFO: falling back to docker compose build tethysdash (10-20 min on weak VMs)"
    if docker compose build tethysdash; then
        echo "OK: image ready (built from source)"
    else
        echo "FAIL: image pull AND build both failed." >&2
        exit 1
    fi
fi

echo ""
echo "✓ setup.sh complete. Next: docker compose up -d"
