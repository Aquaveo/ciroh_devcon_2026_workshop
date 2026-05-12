#!/usr/bin/env bash
#
# install-code-server.sh — install + start code-server on the workshop VM.
#
# Follows the official path from https://github.com/coder/code-server :
#   1. curl -fsSL https://code-server.dev/install.sh | sh
#   2. sudo systemctl enable --now code-server@$USER
#
# Idempotent. Safe to re-run.
#
# Run ONCE per workshop VM. code-server lives on the host (NOT in
# docker-compose) so its integrated terminal is the VM shell — `docker
# compose logs`, `bash scripts/restart-mcp.sh`, etc., all work natively
# from inside the IDE.
#
# Workshop services (tethysdash + two MCP servers) remain in compose
# and are bind-mounted onto the workshop dir; file edits made from
# code-server's editor are visible to those containers via the same
# bind-mount.

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Install (idempotent — official installer is itself idempotent, but we
#    skip the network round-trip if the binary is already present).
# ---------------------------------------------------------------------------
if command -v code-server &>/dev/null; then
    echo "INFO: code-server already installed ($(code-server --version | head -1))"
else
    echo "INFO: installing code-server via the official script"
    curl -fsSL https://code-server.dev/install.sh | sh
fi

# ---------------------------------------------------------------------------
# 2. Enable + start the per-user systemd unit. `enable --now` is idempotent.
# ---------------------------------------------------------------------------
echo "INFO: enabling + starting code-server@${USER}"
sudo systemctl enable --now "code-server@${USER}"

# ---------------------------------------------------------------------------
# 3. Print the password discovery hint. The installer generates a random
#    password at first install in ~/.config/code-server/config.yaml; that
#    file is the source of truth.
# ---------------------------------------------------------------------------
CONFIG_FILE="${HOME}/.config/code-server/config.yaml"

echo ""
echo "✓ code-server is running on 127.0.0.1:8080 inside the VM."
echo ""
if [[ -f "${CONFIG_FILE}" ]]; then
    echo "Password (set by the installer at first run):"
    echo ""
    grep -E '^password:' "${CONFIG_FILE}" | sed 's/^/    /'
    echo ""
else
    echo "WARN: ${CONFIG_FILE} not found yet — re-run after a few seconds:"
    echo "      grep '^password:' ${CONFIG_FILE}"
    echo ""
fi
echo "Expose to your laptop browser by tunneling port 8080 alongside the"
echo "existing forwards:"
echo ""
echo "    bash scripts/tunnel.sh   # prints the ssh -L command"
echo ""
echo "Then open http://localhost:8080 in your laptop browser and paste the"
echo "password above."
