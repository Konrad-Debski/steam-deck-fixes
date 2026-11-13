#!/bin/bash
# Runs as the user at boot. Warns when a SteamOS update removed or changed the fix.
SRC=$(cd "$(dirname "$0")" && pwd)
problems=()
for f in /etc/cm800-vrr-fix/cm800_vrr_fix.py /etc/systemd/system/cm800-vrr-fix.service \
         /etc/udev/rules.d/99-cm800-vrr-fix.rules /etc/atomic-update.conf.d/cm800-vrr-fix.conf; do
  [ -e "$f" ] || problems+=("missing $f")
done
[ -e /etc/cm800-vrr-fix/cm800_vrr_fix.py ] && ! cmp -s "$SRC/cm800_vrr_fix.py" /etc/cm800-vrr-fix/cm800_vrr_fix.py \
  && problems+=("the script in /etc differs from the copy in $SRC")
systemctl is-enabled --quiet cm800-vrr-fix.service 2>/dev/null || problems+=("cm800-vrr-fix.service is not enabled")
uname_now=$(uname -r)
if [ ${#problems[@]} -eq 0 ]; then
  echo "cm800-vrr-fix: OK (kernel $uname_now)"
  rm -f "$HOME/CM800-VRR-FIX-WARNING.txt"
  exit 0
fi
msg="The CM800 dock VRR fix stopped working after a system change: ${problems[*]}. Repair: sudo $SRC/install.sh"
echo "cm800-vrr-fix: $msg" >&2
printf '%s\n' "$msg" "Checked: $(date '+%F %T'), kernel $uname_now" > "$HOME/CM800-VRR-FIX-WARNING.txt"
command -v notify-send >/dev/null && notify-send -u critical "CM800 VRR" "$msg" 2>/dev/null
exit 1
