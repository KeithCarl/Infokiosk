#!/usr/bin/env bash
set -euo pipefail

# Ensure Wayland flags and open the local agent rotator page
URL="http://localhost:8001/rotator"
/usr/bin/cage -s -- \
/usr/bin/chromium-browser \
  --enable-features=UseOzonePlatform \
  --ozone-platform=wayland \
  --kiosk \
  --force-device-scale-factor=1 \
  --noerrdialogs --disable-translate --no-first-run --fast --fast-start \
  --disable-pinch --overscroll-history-navigation=0 \
  --disable-features=TranslateUI \
  "$URL"

