#!/usr/bin/env bash
#
# restart-mcp.sh — restart the nrds_mcps compose service + poll its
# healthcheck until healthy. The primary edit-and-test loop entry point.
#
# Usage: bash scripts/restart-mcp.sh
#
# With the prod nrds-mcps image (plan N-Arch-1), `docker compose restart`
# re-execs the image's built-in `python -m nextgen_mcp.mcp_server`
# entrypoint against the bind-mount-overlaid source under
# repos/nrds_mcps/nextgen_mcp/. Typical time: 1-5 seconds.
#
# Plan reference: Unit 4 (compose service + healthcheck poll) + REQ3.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"
cd "${WORKSHOP_ROOT}"

SERVICE=nrds_mcps
TIMEOUT_S=30
INTERVAL_S=2

if [[ ! -f docker-compose.yml ]]; then
    echo "ERROR: docker-compose.yml not present — Unit 4 hasn't shipped yet." >&2
    echo "       This script is a no-op until the nrds_mcps compose service exists." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Restart the service.
# ---------------------------------------------------------------------------
echo "INFO: restarting compose service '${SERVICE}'"
if ! docker compose restart "${SERVICE}"; then
    echo "FAIL: docker compose restart ${SERVICE} returned non-zero." >&2
    echo "      Likely causes: service not running, syntax error in nrds_mcps source, image missing." >&2
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
            # Until Unit 4 lands the healthcheck stanza this is the path most participants hit.
            echo "WARN: service has no healthcheck defined; falling back to port probe on 9000"
            if curl --max-time 2 -fsS http://localhost:9000/health >/dev/null 2>&1; then
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
