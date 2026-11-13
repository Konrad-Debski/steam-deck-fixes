#!/bin/bash
# Remove the CM800 VRR fix and drop the EDID override. Run with sudo.
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "Uruchom przez sudo" >&2; exit 1; }
systemctl disable --now cm800-vrr-fix.service 2>/dev/null
rm -f /etc/systemd/system/cm800-vrr-fix.service /etc/udev/rules.d/99-cm800-vrr-fix.rules \
      /etc/atomic-update.conf.d/cm800-vrr-fix.conf
rm -rf /etc/cm800-vrr-fix
systemctl daemon-reload; udevadm control --reload
for d in /sys/kernel/debug/dri/[0-9]*/DP-*; do
  # debugfs reports size 0, so test the content: empty means no override.
  [ -n "$(head -c1 "$d/edid_override" 2>/dev/null | od -An -tx1)" ] || continue
  printf reset > "$d/edid_override" && echo 1 > "$d/trigger_hotplug" && echo "reset ${d##*/}"
done
U=${SUDO_USER:-deck}
runuser -u "$U" -- env XDG_RUNTIME_DIR="/run/user/$(id -u "$U")" systemctl --user disable cm800-vrr-fix-check.service 2>/dev/null
rm -f "$(getent passwd "$U" | cut -d: -f6)/.config/systemd/user/cm800-vrr-fix-check.service"
echo "OK: poprawka usunieta"
