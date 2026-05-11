#!/usr/bin/env bash
#
# reset-repos.sh — WIP-protected recovery for a wedged participant clone.
#
# Usage:
#   bash scripts/reset-repos.sh <repo> [--force]
#
#   <repo> is one of: tethysapp-tethys_dash | nrds_mcps
#
# Behavior:
#   - Validates <repo> name (refuses anything else).
#   - Without --force: checks for uncommitted (staged or unstaged) changes
#     via `git status --porcelain`. If non-empty, prints the dirty files
#     and refuses to run any destructive action.
#   - With --force: `git fetch && git reset --hard origin/<default> &&
#     git clean -fd`, then re-checks out the pinned SHA from .env.
#     For tethysapp-tethys_dash: also clears the tethys-persist named volume
#     by running `docker compose -p ciroh_devcon_2026_workshop -f $WORKSHOP_ROOT/docker-compose.yml down -v`.
#     This prevents the stale-init.sh-marker failure (plan finding N5).
#
# Plan reference: Unit 2 contract + PD8 + REQ5.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"
cd "${WORKSHOP_ROOT}"

usage() {
    cat >&2 <<EOF
Usage: bash scripts/reset-repos.sh <repo> [--force]
  <repo>   tethysapp-tethys_dash | nrds_mcps
  --force  destroy uncommitted work in the worktree and reset to upstream

Examples:
  bash scripts/reset-repos.sh nrds_mcps
  bash scripts/reset-repos.sh tethysapp-tethys_dash --force
EOF
}

if [[ $# -lt 1 ]]; then
    usage
    exit 2
fi

REPO="$1"
FORCE="${2:-}"

case "${REPO}" in
    tethysapp-tethys_dash|nrds_mcps) ;;
    *)
        echo "ERROR: invalid repo '${REPO}'." >&2
        usage
        exit 2
        ;;
esac

if [[ -n "${FORCE}" && "${FORCE}" != "--force" ]]; then
    echo "ERROR: unknown argument '${FORCE}' (expected --force or nothing)." >&2
    usage
    exit 2
fi

TARGET="repos/${REPO}"

if [[ ! -d "${TARGET}/.git" ]]; then
    echo "ERROR: ${TARGET} is not a git clone (run setup.sh first)." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# WIP protection: refuse to destroy anything unless --force is explicit.
# ---------------------------------------------------------------------------
DIRTY="$(git -C "${TARGET}" status --porcelain)"

if [[ -n "${DIRTY}" && "${FORCE}" != "--force" ]]; then
    cat >&2 <<EOF
ERROR: ${TARGET} has uncommitted changes:

${DIRTY}

Refusing to discard them. Choices:

  (a) Save your work first:
        cd ${TARGET}
        git stash         # or git commit on a branch
  (b) Force the reset (DESTROYS WIP):
        bash scripts/reset-repos.sh ${REPO} --force
EOF
    exit 1
fi

# ---------------------------------------------------------------------------
# Read pinned SHA so we can re-checkout after the reset.
# ---------------------------------------------------------------------------
if [[ -f .env ]]; then
    # shellcheck source=/dev/null
    set -a; . .env; set +a
else
    echo "ERROR: .env not found. Copy .env.example to .env and fill in SHAs." >&2
    exit 1
fi

case "${REPO}" in
    tethysapp-tethys_dash) PIN_SHA="${TETHYSDASH_SHA:-}";;
    nrds_mcps)             PIN_SHA="${NRDS_MCPS_SHA:-}";;
esac

if [[ -z "${PIN_SHA}" || "${PIN_SHA}" == "TBD" ]]; then
    echo "ERROR: pinned SHA for ${REPO} is unset or TBD in .env." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Reset.
# ---------------------------------------------------------------------------
echo "INFO: fetching origin"
git -C "${TARGET}" fetch --quiet origin

# Detect remote default branch (typically main, sometimes master).
DEFAULT_BRANCH="$(git -C "${TARGET}" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
if [[ -z "${DEFAULT_BRANCH}" ]]; then
    if git -C "${TARGET}" rev-parse --verify origin/main >/dev/null 2>&1; then
        DEFAULT_BRANCH=main
    else
        DEFAULT_BRANCH=master
    fi
fi

echo "INFO: resetting ${TARGET} to origin/${DEFAULT_BRANCH}"
git -C "${TARGET}" reset --hard --quiet "origin/${DEFAULT_BRANCH}"
git -C "${TARGET}" clean -fd --quiet

echo "INFO: re-checking out pinned SHA ${PIN_SHA}"
git -C "${TARGET}" checkout --quiet "${PIN_SHA}"

# ---------------------------------------------------------------------------
# Volume reset for tethysapp-tethys_dash (PD8 / N5 fix).
# ---------------------------------------------------------------------------
if [[ "${REPO}" == "tethysapp-tethys_dash" ]]; then
    if [[ -f "${WORKSHOP_ROOT}/docker-compose.yml" ]]; then
        echo "INFO: clearing tethys-persist named volume (paired with tethysapp-tethys_dash reset)"
        docker compose \
            -p ciroh_devcon_2026_workshop \
            -f "${WORKSHOP_ROOT}/docker-compose.yml" \
            down --volumes --remove-orphans 2>/dev/null || \
            echo "WARN: docker compose down -v failed (stack may already be down)"
    else
        echo "WARN: docker-compose.yml not present yet (Unit 3 hasn't shipped); skipping volume reset"
    fi
fi

echo ""
echo "✓ ${TARGET} reset to ${PIN_SHA} (origin/${DEFAULT_BRANCH} HEAD applied first)"
