#!/bin/bash
# Runs as the user at boot. Warns when a SteamOS update removed or changed the fix.
SRC=$(cd "$(dirname "$0")" && pwd)
problems=()
for f in /etc/cm800-vrr-fix/cm800_vrr_fix.py /etc/systemd/system/cm800-vrr-fix.service \
         /etc/udev/rules.d/99-cm800-vrr-fix.rules /etc/atomic-update.conf.d/cm800-vrr-fix.conf; do
  [ -e "$f" ] || problems+=("brak $f")
done
[ -e /etc/cm800-vrr-fix/cm800_vrr_fix.py ] && ! cmp -s "$SRC/cm800_vrr_fix.py" /etc/cm800-vrr-fix/cm800_vrr_fix.py \
  && problems+=("skrypt w /etc rozni sie od kopii w $SRC")
systemctl is-enabled --quiet cm800-vrr-fix.service 2>/dev/null || problems+=("usluga cm800-vrr-fix.service nie jest wlaczona")
uname_now=$(uname -r)
if [ ${#problems[@]} -eq 0 ]; then
  echo "cm800-vrr-fix: OK (kernel $uname_now)"
  rm -f "$HOME/CM800-VRR-FIX-UWAGA.txt"
  exit 0
fi
msg="Poprawka VRR dla docka CM800 nie dziala po zmianie systemu: ${problems[*]}. Napraw: sudo $SRC/install.sh"
echo "cm800-vrr-fix: $msg" >&2
printf '%s\n' "$msg" "Sprawdzono: $(date '+%F %T'), kernel $uname_now" > "$HOME/CM800-VRR-FIX-UWAGA.txt"
command -v notify-send >/dev/null && notify-send -u critical "CM800 VRR" "$msg" 2>/dev/null
exit 1
