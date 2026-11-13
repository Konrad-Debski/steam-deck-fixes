#!/bin/bash
# On-device regression test: the service must restore the override after a
# hotplug without losing the display. It once wrote a bare "1" to amdgpu's
# trigger_hotplug, which the driver parsed as 0 (simulated unplug, TV black).
# Drops the override and fires a hotplug, so udev starts cm800-vrr-fix.service.
# PASS = after WAIT seconds DP-1 is connected and the FreeSync override is back.
# Run as root. Usage: repro-hotplug-race.sh [wait_seconds]
WAIT=${1:-60}
DBG=/sys/kernel/debug/dri/0/DP-1
printf reset > $DBG/edid_override
echo 1 > $DBG/trigger_hotplug
t0=$(date +%s)
while :; do
  sleep 2
  st=$(cat /sys/class/drm/card0-DP-1/status)
  ov=$(head -c 256 $DBG/edid_override | wc -c)
  active=$(systemctl is-active cm800-vrr-fix.service)
  if [ "$st" = connected ] && [ "$ov" = 256 ] && [ "$active" != activating ]; then
    echo "PASS after $(( $(date +%s) - t0 )) s: connected, override active"; exit 0
  fi
  if [ $(( $(date +%s) - t0 )) -ge "$WAIT" ]; then
    echo "FAIL after $WAIT s: status=$st override_bytes=$ov service=$active"; exit 1
  fi
done
