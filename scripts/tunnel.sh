#!/usr/bin/env bash
#
# tunnel.sh — print the SSH -L command for the workshop tunnel.
#
# The chatbox in the participant's laptop browser reaches the two MCP
# servers on `localhost:9000` (nrds_mcps, data layer) and `localhost:9001`
# (tethysdash_mcps, visualization layer) via the -L forwards, NOT via
# compose-internal DNS. The TethysDash UI sits behind `localhost:8000`
# (also via -L). All three ports must be tunneled or the workshop's
# edit-and-test loop breaks.
#
# Usage:
#   bash scripts/tunnel.sh                  # prompts for VM host if no env var
#   bash scripts/tunnel.sh user@vm-host     # one-shot
#   VM_HOST=user@vm-host bash scripts/tunnel.sh
#
# This script prints the SSH command to stdout for copy-paste. It does NOT
# open the tunnel itself — participants run the printed command in a
# separate laptop terminal (the workshop devcontainer can't reach back to
# the laptop).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"
cd "${WORKSHOP_ROOT}"

# Source .env if present so VM_HOST from there is picked up.
if [[ -f .env ]]; then
    # shellcheck source=/dev/null
    set -a; . .env; set +a
fi

# Resolution order: CLI arg > $VM_HOST env > interactive prompt > error.
host=""
if [[ $# -ge 1 && -n "$1" ]]; then
    host="$1"
elif [[ -n "${VM_HOST:-}" ]]; then
    host="${VM_HOST}"
fi

if [[ -z "${host}" ]]; then
    # Only prompt if stdin is a tty; otherwise we'd hang in CI / non-interactive
    # contexts and the user would have no signal what went wrong.
    if [[ -t 0 ]]; then
        echo "VM_HOST is not set in .env and no argument was given." >&2
        printf 'Enter your VM host (e.g. user@workshop-vm-12.access.example.org): ' >&2
        read -r host
        if [[ -z "${host}" ]]; then
            echo "ERROR: empty host." >&2
            exit 1
        fi
    else
        cat >&2 <<EOF
ERROR: VM host not specified.

Provide one of:
  - First argument:  bash scripts/tunnel.sh user@vm-host
  - Env var:         VM_HOST=user@vm-host bash scripts/tunnel.sh
  - .env entry:      VM_HOST=user@vm-host
EOF
        exit 1
    fi
fi

# ServerAliveInterval keeps the tunnel up across NAT idle timeouts; without
# it, the -L 9000/9001 forwards sometimes die silently mid-workshop while
# -L 8000 survives (see README troubleshooting "chatbox can't reach MCP but
# UI works").
cat <<EOF
# Run this command in a NEW laptop terminal (NOT inside the devcontainer):

ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \\
    -L 8000:localhost:8000 \\
    -L 9000:localhost:9000 \\
    -L 9001:localhost:9001 \\
    ${host}

# Then open http://localhost:8000 in your laptop browser.
# Keep this ssh session open for the duration of the workshop.
EOF
