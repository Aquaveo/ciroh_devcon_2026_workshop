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

# Resolve workshop root from the script's own location so the drop-in
# below opens the right folder even if the repo is cloned somewhere other
# than ~/workshops/devcon.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
WORKSHOP_ROOT="$(dirname -- "${SCRIPT_DIR}")"

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
# 2. Configure code-server to open the workshop dir on launch.
#
# Drop-in override (NOT modification of the shipped unit file) so package
# updates to code-server don't clobber the change. Standard systemd
# pattern: the empty `ExecStart=` line clears the inherited value
# before the second line redefines it with the workshop dir appended.
# ---------------------------------------------------------------------------
CODE_SERVER_BIN="$(command -v code-server)"
DROPIN_DIR="/etc/systemd/system/code-server@${USER}.service.d"
echo "INFO: setting code-server's default workspace to ${WORKSHOP_ROOT}"
sudo mkdir -p "${DROPIN_DIR}"
sudo tee "${DROPIN_DIR}/workspace.conf" >/dev/null <<EOF
[Service]
ExecStart=
ExecStart=${CODE_SERVER_BIN} ${WORKSHOP_ROOT}
EOF
sudo systemctl daemon-reload

# ---------------------------------------------------------------------------
# 3. Enable + start the per-user systemd unit. `enable --now` is idempotent;
#    `restart` picks up the drop-in's new ExecStart on re-runs of this script.
# ---------------------------------------------------------------------------
echo "INFO: enabling + starting code-server@${USER}"
sudo systemctl enable --now "code-server@${USER}"
sudo systemctl restart "code-server@${USER}"

# ---------------------------------------------------------------------------
# 4. Print the password discovery hint. The installer generates a random
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
