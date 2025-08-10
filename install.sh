#!/usr/bin/env bash
set -euo pipefail

ROLE=""
NAME=""
PEERS=""
ADMIN_PASSWORD=""
AGENT_TOKEN=""
SECRET_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --peers) PEERS="$2"; shift 2;;
    --admin-password) ADMIN_PASSWORD="$2"; shift 2;;
    --agent-token) AGENT_TOKEN="$2"; shift 2;;
    --secret-key) SECRET_KEY="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "${ROLE}" || -z "${NAME}" ]]; then
  echo "Usage: sudo ./install.sh --role [agent|admin] --name <KioskName> [--peers host1,host2] [--admin-password pass] [--agent-token token] [--secret-key key]"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run with sudo."
  exit 1
fi

# Packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  chromium-browser cage jq python3 python3-pip python3-venv \
  avahi-daemon libgles2-mesa

# Create layout
install -d -o pi -g pi /opt/infokiosk
cp -r agent admin kiosk common /opt/infokiosk/
chown -R pi:pi /opt/infokiosk

# Python deps (system-wide, small footprint)
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r /opt/infokiosk/common/requirements.txt

# Config dir
install -d /etc/infokiosk
echo "THIS_KIOSK_NAME=${NAME}" > /etc/infokiosk/common.env

# Secrets
AGENT_TOKEN=${AGENT_TOKEN:-$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32)}
SECRET_KEY=${SECRET_KEY:-$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32)}

# Agent env + config
cat >/etc/infokiosk/agent.env <<EOF
AGENT_BIND=0.0.0.0
AGENT_PORT=8001
AGENT_TOKEN=${AGENT_TOKEN}
SECRET_KEY=${SECRET_KEY}
EOF

if [[ ! -f /etc/infokiosk/agent.json ]]; then
  cp /opt/infokiosk/agent/config.default.json /etc/infokiosk/agent.json
  jq --arg n "$NAME" '.name=$n' /etc/infokiosk/agent.json > /etc/infokiosk/agent.json.new
  mv /etc/infokiosk/agent.json.new /etc/infokiosk/agent.json
fi

# Admin env
if [[ "$ROLE" == "admin" ]]; then
  ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme}
  cat >/etc/infokiosk/admin.env <<EOF
ADMIN_BIND=0.0.0.0
ADMIN_PORT=8000
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SECRET_KEY=${SECRET_KEY}
AGENT_TOKEN=${AGENT_TOKEN}
KIOSK_PEERS=${PEERS:-Infopoint1.local,InfoPoint2.local}
EOF
  # Optional persisted list
  cat >/etc/infokiosk/admin.json <<EOF
{"peers":{
  "Infopoint1":"Infopoint1.local",
  "InfoPoint2":"InfoPoint2.local"
}}
EOF
fi

# Services
install -m 644 /opt/infokiosk/agent/service.infokiosk-agent.service /etc/systemd/system/infokiosk-agent.service
systemctl daemon-reload
systemctl enable --now infokiosk-agent.service

if [[ "$ROLE" == "admin" ]]; then
  install -m 644 /opt/infokiosk/admin/service.infokiosk-admin.service /etc/systemd/system/infokiosk-admin.service
  systemctl daemon-reload
  systemctl enable --now infokiosk-admin.service
fi

# Kiosk user service
install -m 755 /opt/infokiosk/kiosk/chromium-kiosk.sh /opt/infokiosk/kiosk/chromium-kiosk.sh
chown pi:pi /opt/infokiosk/kiosk/chromium-kiosk.sh
install -m 644 /opt/infokiosk/kiosk/kiosk.service /etc/systemd/user/kiosk.service
loginctl enable-linger pi

# Auto-login to console (so user service starts on boot)
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_boot_behaviour B4 || true   # Console Autologin
fi

# Sudoers for reboot
bash /opt/infokiosk/scripts/set-sudoers-infokiosk

# Enable kiosk for user pi
sudo -u pi systemctl --user daemon-reload
sudo -u pi systemctl --user enable --now kiosk.service

echo
echo "=============================================="
echo " Infokiosk installed on ${NAME} as role: ${ROLE}"
if [[ "$ROLE" == "admin" ]]; then
  echo " Admin UI: http://$(hostname -I | awk '{print $1}'):8000"
  echo " Login password: ${ADMIN_PASSWORD}"
fi
echo " Agent token (keep safe): ${AGENT_TOKEN}"
echo "=============================================="
