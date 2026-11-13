#!/bin/bash
# Install the CM800 VRR fix. Run: sudo ~/.local/share/cm800-vrr-fix/install.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Uruchom przez sudo" >&2; exit 1; }
SRC=$(cd "$(dirname "$0")" && pwd)
install -D -o root -g root -m 0755 "$SRC/cm800_vrr_fix.py" /etc/cm800-vrr-fix/cm800_vrr_fix.py
install -D -o root -g root -m 0644 "$SRC/etc/cm800-vrr-fix.service" /etc/systemd/system/cm800-vrr-fix.service
install -D -o root -g root -m 0644 "$SRC/etc/99-cm800-vrr-fix.rules" /etc/udev/rules.d/99-cm800-vrr-fix.rules
install -D -o root -g root -m 0644 "$SRC/etc/cm800-vrr-fix.conf" /etc/atomic-update.conf.d/cm800-vrr-fix.conf
udevadm control --reload
systemctl daemon-reload
systemctl enable cm800-vrr-fix.service
systemctl start cm800-vrr-fix.service
# Post-update check runs as the user at every boot (lives in /home, survives updates).
U=${SUDO_USER:-deck}
UH=$(getent passwd "$U" | cut -d: -f6)
install -D -o "$U" -g "$U" -m 0644 "$SRC/user/cm800-vrr-fix-check.service" "$UH/.config/systemd/user/cm800-vrr-fix-check.service"
runuser -u "$U" -- env XDG_RUNTIME_DIR="/run/user/$(id -u "$U")" systemctl --user daemon-reload
runuser -u "$U" -- env XDG_RUNTIME_DIR="/run/user/$(id -u "$U")" systemctl --user enable cm800-vrr-fix-check.service
journalctl -u cm800-vrr-fix.service -b --no-pager -n 5 -o cat
echo "OK: poprawka zainstalowana"
