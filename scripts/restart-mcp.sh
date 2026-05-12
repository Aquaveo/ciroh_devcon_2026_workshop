#!/usr/bin/env bash
#
# restart-mcp.sh — restart one of the MCP compose services + poll its
# healthcheck until healthy. The primary edit-and-test loop entry point.
#
# Usage:
#   bash scripts/restart-mcp.sh                  # defaults to nrds_mcps
#   bash scripts/restart-mcp.sh nrds_mcps
#   bash scripts/restart-mcp.sh tethysdash_mcps
#
# `docker compose restart` re-execs each image's entrypoint against the
# bind-mount-overlaid source under repos/<repo>/. Typical time: 1-5 seconds.
#
# Plan references:
#   docs/plans/2026-05-11-001-feat-tethysdash-mcp-workshop-orchestration-plan.md
#     Unit 4 (initial nrds_mcps version) + REQ3
#   docs/plans/2026-05-11-008-feat-workshop-add-tethysdash-mcps-plan.md
#     Unit 4 (generalize to allowlisted service-name arg)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"
cd "${WORKSHOP_ROOT}"

# Positional service-name arg. Allowlist enforced below. Default preserves
# back-compat for the original `bash scripts/restart-mcp.sh` invocation
# documented in the README skeleton before plan 008.
SERVICE="${1:-nrds_mcps}"

# Allowlist + per-service fallback port for the no-healthcheck branch below.
case "${SERVICE}" in
    nrds_mcps)        FALLBACK_PORT=9000 ;;
    tethysdash_mcps)  FALLBACK_PORT=9001 ;;
    *)
        echo "ERROR: unknown service '${SERVICE}'." >&2
        echo "       Valid services: nrds_mcps, tethysdash_mcps" >&2
        exit 1
        ;;
esac

TIMEOUT_S=30
INTERVAL_S=2

if [[ ! -f docker-compose.yml ]]; then
    echo "ERROR: docker-compose.yml not present in ${WORKSHOP_ROOT}." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Restart the service.
# ---------------------------------------------------------------------------
echo "INFO: restarting compose service '${SERVICE}'"
if ! docker compose restart "${SERVICE}"; then
    echo "FAIL: docker compose restart ${SERVICE} returned non-zero." >&2
    echo "      Likely causes: service not running, syntax error in bind-mounted source, image missing." >&2
    echo "      Diagnose: docker compose logs --tail=50 ${SERVICE}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Healthcheck poll — use `docker inspect` (stable across compose CLI versions
# per pass-1 plan review F-Compose-PS).
# ---------------------------------------------------------------------------
container_id="$(docker compose ps -q "${SERVICE}" 2>/dev/null || true)"
if [[ -z "${container_id}" ]]; then
    echo "FAIL: could not resolve container id for service '${SERVICE}'." >&2
    echo "      Is the service defined in docker-compose.yml? Did `up -d` ever succeed?" >&2
    exit 1
fi

echo "INFO: polling healthcheck (up to ${TIMEOUT_S}s, every ${INTERVAL_S}s)"

deadline=$(( SECONDS + TIMEOUT_S ))
status=""
while (( SECONDS < deadline )); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "${container_id}" 2>/dev/null || echo 'inspect-failed')"
    case "${status}" in
        healthy)
            echo "OK: ${SERVICE} is healthy"
            echo ""
            echo "----- last 20 log lines -----"
            docker compose logs --tail=20 "${SERVICE}" 2>&1 || true
            echo "-----------------------------"
            exit 0
            ;;
        unhealthy)
            echo "FAIL: ${SERVICE} is unhealthy" >&2
            echo "" >&2
            echo "----- last 50 log lines -----" >&2
            docker compose logs --tail=50 "${SERVICE}" >&2 2>&1 || true
            echo "-----------------------------" >&2
            exit 1
            ;;
        no-healthcheck)
            # Compose service has no HEALTHCHECK defined — fall back to a port probe.
            echo "WARN: service has no healthcheck defined; falling back to port probe on ${FALLBACK_PORT}"
            if curl --max-time 2 -fsS "http://localhost:${FALLBACK_PORT}/health" >/dev/null 2>&1; then
                echo "OK: ${SERVICE} answers /health (port-probe fallback)"
                exit 0
            fi
            ;;
        starting|inspect-failed|"")
            : # keep polling
            ;;
        *)
            echo "WARN: unexpected health status '${status}'; continuing to poll"
            ;;
    esac
    sleep "${INTERVAL_S}"
done

echo "FAIL: ${SERVICE} did not become healthy within ${TIMEOUT_S}s (last status: ${status})" >&2
echo "" >&2
echo "----- last 50 log lines -----" >&2
docker compose logs --tail=50 "${SERVICE}" >&2 2>&1 || true
echo "-----------------------------" >&2
exit 1
