# Infokiosk – Raspberry Pi Wayland Chromium Kiosk with Admin UI

A lightweight multi-Pi information kiosk system:
- Two Raspberry Pis: `Infopoint1` and `InfoPoint2`
- One Pi runs the **Admin UI** (also a kiosk)
- Add/remove URLs with per-item timeouts
- Reboot either kiosk from the admin site
- Wayland + Cage + Chromium for stable kiosk mode
- Headless Raspberry Pi OS Lite compatible

---

## Features

- **Multi-device control** – Manage multiple kiosks from one admin interface
- **Custom playlists** – URL list with per-URL display timeouts
- **Reboot control** – One-click reboot per kiosk
- **True kiosk mode** – No desktop, just Chromium in Wayland Cage
- **LAN-friendly** – Uses mDNS (`.local`) to auto-discover peers

---

## Requirements

- Raspberry Pi 4 (2GB+ recommended)
- Raspberry Pi OS Lite 64-bit (Bookworm)
- Hostnames set to `Infopoint1` and `InfoPoint2` (or change in install args)

---

## Installation

**On both Pis**  
```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/<yourusername>/infokiosk.git
cd infokiosk

Admin Pi (Infopoint1)

bash
Copy
Edit
sudo bash ./install.sh --role admin --name Infopoint1 \
  --peers Infopoint1.local,InfoPoint2.local \
  --admin-password 'changeme'
Agent Pi (Infopoint2)

bash
Copy
Edit
sudo bash ./install.sh --role agent --name InfoPoint2
Reboot both Pis after install:

bash
Copy
Edit
sudo reboot
Usage
Admin UI: http://Infopoint1.local:8000

Login with the password you set in --admin-password

Add/remove URLs, set timeouts, reboot kiosks

Kiosks auto-boot into Chromium showing the playlist

Security Notes
Admin password and agent token are stored in /etc/infokiosk/*.env

Change them if you deploy outside a trusted LAN

For public deployment, use HTTPS and firewall rules

License
MIT
