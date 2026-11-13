#!/usr/bin/env python3
"""Measure the real scanout rate of a CRTC from the DRM vblank counter.

With VRR active the GPU stretches vblank, so the measured rate drops below the
mode's nominal refresh. Usage: vblank_rate.py [crtc_index] [seconds] [windows]
"""
import ctypes, fcntl, os, struct, sys, time

DRM_IOCTL_WAIT_VBLANK = 0xC018643A  # _IOWR('d', 0x3a, union drm_wait_vblank), 24 bytes
DRM_VBLANK_RELATIVE = 0x1
HIGH_CRTC_SHIFT, HIGH_CRTC_MASK = 1, 0x3E

import json, subprocess
def dp_crtc_index():
    dev = json.loads(subprocess.run(["drm_info", "-j"], capture_output=True, text=True).stdout)["/dev/dri/card0"]
    conn = next(c for c in dev["connectors"] if c["type"] == 10)  # DisplayPort (USB-C to dock)
    cid = conn["properties"]["CRTC_ID"]["value"]
    return [c["id"] for c in dev["crtcs"]].index(cid)
crtc = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "auto" else dp_crtc_index()
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
windows = int(sys.argv[3]) if len(sys.argv) > 3 else 5

fd = os.open("/dev/dri/card0", os.O_RDWR)
vtype = DRM_VBLANK_RELATIVE | ((crtc << HIGH_CRTC_SHIFT) & HIGH_CRTC_MASK)

def query():
    buf = bytearray(struct.pack("IIQQ", vtype, 0, 0, 0))  # union is 24 bytes (reply side)
    fcntl.ioctl(fd, DRM_IOCTL_WAIT_VBLANK, buf)
    _, seq, sec, usec = struct.unpack("IIqq", bytes(buf))
    return seq, sec + usec / 1e6

rates = []
for _ in range(windows):
    s0, t0 = query()
    time.sleep(secs)
    s1, t1 = query()
    rates.append((s1 - s0) / (t1 - t0) if t1 > t0 else float("nan"))
print(f"crtc index {crtc}: vblank rate per window (Hz): " + " ".join(f"{r:.1f}" for r in rates))
