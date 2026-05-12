#!/usr/bin/env bash
#
# setup.sh — workshop bootstrap.
#
# Idempotent. Safe to re-run.
#
# Steps:
#   1. Read pinned SHAs + image tag from .env (fallback: .env.example).
#   2. Clone-or-pull Aquaveo/tethysapp-tethys_dash and Aquaveo/nrds_mcps into
#      ./repos/, then check out the pinned SHAs (detached HEAD).
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

# Both SHAs and both image tags are required.
require_var TETHYSDASH_SHA       || exit 1
require_var NRDS_MCPS_SHA        || exit 1
require_var IMAGE_TAG            || exit 1
require_var NRDS_MCPS_IMAGE_TAG  || exit 1

# ---------------------------------------------------------------------------
# 2. Clone-or-pull the two repos. Per-repo strict failure.
# ---------------------------------------------------------------------------
clone_or_pull() {
    local repo_name="$1"        # tethysapp-tethys_dash or nrds_mcps
    local sha="$2"
    local target="repos/${repo_name}"
    local url="https://github.com/Aquaveo/${repo_name}.git"

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

clone_or_pull tethysapp-tethys_dash "${TETHYSDASH_SHA}" || exit 1
clone_or_pull nrds_mcps             "${NRDS_MCPS_SHA}"  || exit 1

# ---------------------------------------------------------------------------
# 2b. Bundle-presence guard (Q7c in docs/pre-conditions.md).
#
# The TethysDash devcontainer Dockerfile is Python-only (python:3.11-slim, no
# Node/webpack). It does `COPY . .`, so the React bundle that ends up in the
# image is exactly what's committed under tethysapp/tethysdash/public/frontend/
# at TETHYSDASH_SHA. The repo convention is a `chore(bundle): rebuild ...`
# commit after every webpack change. If the pinned SHA predates that commit
# (or sits on a feature branch where the bundle was never updated), Django
# silently serves stale or absent React UI.
#
# This guard catches the worst case — bundle dir empty / main.js missing —
# at setup time, so the failure surfaces here instead of "blank page in the
# browser after 90s boot". It does NOT detect JSX-vs-bundle drift (a fresh-
# looking dir whose chunks predate the committed JSX); that's what Q7c's
# manual `npm run build && git status` check is for.
# ---------------------------------------------------------------------------
TETHYSDASH_BUNDLE_ENTRY="repos/tethysapp-tethys_dash/tethysapp/tethysdash/public/frontend/main.js"
if [[ ! -s "${TETHYSDASH_BUNDLE_ENTRY}" ]]; then
    echo "FAIL: ${TETHYSDASH_BUNDLE_ENTRY} is missing or empty at TETHYSDASH_SHA." >&2
    echo "      The devcontainer image ships the committed React bundle as-is" >&2
    echo "      (no Node/webpack at build time). Pin a SHA on or right after a" >&2
    echo "      'chore(bundle): rebuild ...' commit, or rebuild + commit and repin." >&2
    echo "      See docs/pre-conditions.md Q7c." >&2
    exit 1
fi
echo "OK: TethysDash bundle present at pinned SHA (main.js found)."

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
