#!/usr/bin/env bash
# Probe: does the Deck drive DP-1 (dock -> LG G3) at 3840x2160@120 with VRR on,
# without new amdgpu warnings since the previous run?
# Run as root. Exit 0 = kernel side green, 1 = red.
# Usage: sudo probe.sh [samples] [interval_s]
set -u
SAMPLES=${1:-20}
INTERVAL=${2:-0.25}
DIR=$(cd "$(dirname "$0")" && pwd)
STATE=$DIR/.last_dmesg_ts
DBG=/sys/kernel/debug/dri/0/DP-1
CONN=/sys/class/drm/card0-DP-1

fail=0
say() { printf '%-5s %s\n' "$1" "$2"; [ "$1" = FAIL ] && fail=1; return 0; }

echo "== probe $(date '+%F %T')  session: $(pgrep -f '^gamescope ' >/dev/null && echo 'Game Mode (gamescope)' || (pgrep -x kwin_wayland >/dev/null && echo 'Desktop (KWin)' || echo unknown))"

[ "$(cat $CONN/status)" = connected ] && say OK "DP-1 connected" || say FAIL "DP-1 not connected"

# Sample DRM state several times: gamescope may toggle VRR_ENABLED per focus/frame.
python3 -I - "$SAMPLES" "$INTERVAL" <<'PY' || fail=1
import json, subprocess, sys, time
n, dt = int(sys.argv[1]), float(sys.argv[2])
modes, vrr_on, planes, cap = [], 0, [], None
for i in range(n):
    d = json.loads(subprocess.run(["drm_info", "-j"], capture_output=True, text=True).stdout)
    dev = d["/dev/dri/card0"]
    # DRM_MODE_CONNECTOR_DisplayPort = 10 (the USB-C DP alt-mode output to the dock)
    conn = next((c for c in dev["connectors"] if c["type"] == 10 and c["properties"]["CRTC_ID"]["value"]), None)
    if conn is None:
        print("FAIL  no active DP connector"); sys.exit(1)
    cap = conn["properties"]["vrr_capable"]["value"]
    crtc_id = conn["properties"]["CRTC_ID"]["value"]
    crtc = next(c for c in dev["crtcs"] if c["id"] == crtc_id)
    m = crtc["mode"]
    modes.append(f'{m["hdisplay"]}x{m["vdisplay"]}@{m["vrefresh"]} ({m["clock"]/1000:.0f} MHz)')
    vrr_on += crtc["properties"]["VRR_ENABLED"]["value"]
    planes.append(sum(1 for p in dev["planes"] if p.get("crtc_id") == crtc_id and p.get("fb_id")))
    time.sleep(dt)
ok = True
mode_set = sorted(set(modes))
if mode_set == ["3840x2160@120 (1188 MHz)"]:
    print(f"OK    mode {mode_set[0]} in {n}/{n} samples")
else:
    print(f"FAIL  mode(s) seen: {mode_set}"); ok = False
print(("OK   " if cap == 1 else "FAIL ") + f" vrr_capable={cap}")
ok &= cap == 1
print(("OK   " if vrr_on == n else "FAIL ") + f" VRR_ENABLED=1 in {vrr_on}/{n} samples")
ok &= vrr_on == n
print(f"INFO  active planes on CRTC: min {min(planes)} max {max(planes)}")
sys.exit(0 if ok else 1)
PY

ls=$(tr -s ' \n' ' ' < $DBG/link_settings | awk '{print $2, $3}')
lanes=${ls%% *}; rate=${ls##* }
case $rate in 0x1e) r="HBR3 8.1G";; 0x14) r="HBR2 5.4G";; 0xa) r="HBR 2.7G";; *) r=$rate;; esac
say INFO "DP link: $lanes lanes x $r, DSC clock enabled=$(tr -d ' \n\0' < $DBG/dsc_clock_en), DSC bpp x16=$(tr -d ' \n\0' < $DBG/dsc_bits_per_pixel), vrr_range $(tr '\n' ' ' < $DBG/vrr_range)"

# Which VRR signalling does amdgpu send to the dock? The Valve kernel logs it per
# commit at drm.debug 0x6: "as_type = A, packet_type = P". With this dock,
# P=4 (HDMI VRR / VTEM, left to the PCON) never reached the TV; P=2 (FreeSync v2)
# did (TV showed "VRR on"). Needs at least one flip during the window.
dbg_prev=$(cat /sys/module/drm/parameters/debug)
mark=$(dmesg | tail -1 | awk -F'[][]' '{print $2+0}')
echo 0x6 > /sys/module/drm/parameters/debug; sleep 1.5; echo "$dbg_prev" > /sys/module/drm/parameters/debug
pt=$(dmesg | awk -v t="$mark" -F'[][]' '$2+0 > t+0' | grep -o 'packet_type = [0-9]*' | tail -1 | grep -o '[0-9]*$')
case $pt in
  4) say FAIL "VRR packet: HDMI VRR (VTEM via PCON). This dock does not pass it to the TV.";;
  1|2|3) say OK "VRR packet: FreeSync v$pt info packet";;
  0) say FAIL "VRR packet: plain DP Adaptive-Sync only, no FreeSync info packet";;
  *)
    # No flip seen. Fall back to the rule the kernel applies to whitelisted PCONs:
    # HF-VSDB VRRmin in 1..48 (and VRRmax 0 or >= 100) => HDMI VRR is preferred.
    hv=$(python3 -I - "$CONN/edid" <<'PY'
import sys
e = open(sys.argv[1], "rb").read()
for b in range(128, len(e), 128):
    if e[b] != 0x02: continue
    p, end = b + 4, b + e[b + 2]
    while p < end:
        tag, ln = e[p] >> 5, e[p] & 0x1F
        if tag == 3 and e[p+1:p+4] == bytes([0xD8, 0x5D, 0xC4]) and ln >= 10:
            vmin, vmax = e[p+9] & 0x3F, ((e[p+9] & 0xC0) << 2) | e[p+10]
            print(1 if 1 <= vmin <= 48 and (vmax == 0 or vmax >= 100) else 0); sys.exit()
        p += ln + 1
print(0)
PY
)
    if [ "$hv" = 1 ]; then say FAIL "VRR packet (from EDID rule, no flip seen): HDMI VRR via PCON. This dock does not pass it to the TV."
    else say OK "VRR packet (from EDID rule, no flip seen): FreeSync info packet"; fi;;
esac

# Kernel log since previous run.
last=$(cat "$STATE" 2>/dev/null || echo 0)
new=$(dmesg | awk -v t="$last" -F'[][]' '{ if ($2+0 > t+0) print }')
now=$(dmesg | tail -1 | awk -F'[][]' '{print $2+0}')
echo "$now" > "$STATE"
bad=$(printf '%s\n' "$new" | grep -E 'cut here|\] WARNING: |\*ERROR\*|flip_done timed out|BUG:|link training fail' | grep -v '^$')
streams=$(printf '%s\n' "$new" | grep -c 'HDR SB:01')
if [ -n "$bad" ]; then
  say FAIL "new kernel warnings since last run:"; printf '%s\n' "$bad" | head -12 | sed 's/^/      /'
else
  say OK "no new amdgpu warnings since last run"
fi
say INFO "stream info-packet updates since last run (HDR SB lines, roughly one per modeset): $streams"

[ $fail = 0 ] && echo "VERDICT: GREEN (kernel side)" || echo "VERDICT: RED"
exit $fail
