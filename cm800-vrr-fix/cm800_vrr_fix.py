#!/usr/bin/python3 -I
"""Make the Valve amdgpu kernel send FreeSync through the Ugreen CM800 dock.

With a TV that lists HDMI VRR in its HDMI Forum VSDB, the kernel skips FreeSync
packets for whitelisted DP->HDMI converters and leaves HDMI VRR to the
converter. The CM800 converter (Synaptics, ID "cHDMIb") never triggers it, so
the TV gets fixed 120 Hz. Zeroing VRRmin/VRRmax in an EDID override makes the
kernel fall back to FreeSync, which this dock passes through.
"""

HF_VSDB_OUI = bytes([0xD8, 0x5D, 0xC4])  # C4-5D-D8, little endian in the block
AMD_VSDB_OUI = bytes([0x1A, 0x00, 0x00])  # 00-00-1A, FreeSync over HDMI
# DPCD 0x500 (branch OUI) and 0x503 (6-byte device ID) of the CM800 converter.
CM800_BRANCH = (bytes.fromhex("90cc24"), b"cHDMIb")


EDID_HEADER = bytes([0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0])


def valid_edid(e):
    """Header, length from the extension count, and every block checksum."""
    if len(e) < 128 or e[:8] != EDID_HEADER or len(e) != 128 * (1 + e[126]):
        return False
    return all(sum(e[b:b + 128]) % 256 == 0 for b in range(0, len(e), 128))


def _cta_blocks(e):
    for b in range(128, len(e), 128):
        if e[b] == 0x02:
            yield b


def _data_blocks(e, b):
    p, end = b + 4, b + e[b + 2]
    while p < end:
        tag, ln = e[p] >> 5, e[p] & 0x1F
        yield p, tag, ln
        p += ln + 1


def desired_override(edid, branch_oui, branch_id):
    """Return the EDID override to apply, or None for no override."""
    if (bytes(branch_oui), bytes(branch_id)) != CM800_BRANCH:
        return None
    if not valid_edid(edid):
        return None
    e = bytearray(edid)
    has_freesync = any(
        tag == 3 and e[p + 1:p + 4] == AMD_VSDB_OUI
        for b in _cta_blocks(e) for p, tag, ln in _data_blocks(e, b)
    )
    if not has_freesync:
        return None
    patched = False
    for b in _cta_blocks(e):
        for p, tag, ln in _data_blocks(e, b):
            if tag == 3 and e[p + 1:p + 4] == HF_VSDB_OUI and ln >= 10:
                # Same rule as drm_parse_vrr_info() in the kernel.
                vmin, vmax = e[p + 9] & 0x3F, ((e[p + 9] & 0xC0) << 2) | e[p + 10]
                if 1 <= vmin <= 48 and (vmax == 0 or vmax >= 100):
                    e[p + 9] = 0
                    e[p + 10] = 0
                    e[b + 127] = (-sum(e[b:b + 127])) & 0xFF
                    patched = True
    return bytes(e) if patched else None


# --- Device side (runs as root from cm800-vrr-fix.service) -------------------

import fcntl
import glob
import os
import sys
import time

I2C_SLAVE = 0x0703


def log(msg):
    print(msg, flush=True)


def read_branch(aux_dev):
    fd = os.open(aux_dev, os.O_RDONLY)
    try:
        return os.pread(fd, 3, 0x500), os.pread(fd, 6, 0x503)
    finally:
        os.close(fd)


def read_edid(i2c_dev):
    """Real EDID over DDC (I2C over DP AUX). Bypasses the kernel EDID override."""
    fd = os.open(i2c_dev, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE, 0x50)
        data = b""
        for off in range(0, 256, 16):
            os.write(fd, bytes([off]))
            data += os.read(fd, 16)
            if off == 112 and data[126] == 0:
                break
        return data[:128 * (1 + data[126])] if data[126] <= 1 else None
    finally:
        os.close(fd)


def sub_dev(conn_dir, pattern):
    hits = glob.glob(os.path.join(conn_dir, pattern))
    return "/dev/" + os.path.basename(hits[0]) if hits else None


def trigger_hotplug(dbg):
    """Ask amdgpu to re-detect the connector.
    amdgpu's debugfs parser always reads 42 bytes from the caller's buffer, no
    matter how many were written. A bare "1" is followed by leftover memory,
    fails to parse and counts as 0, which means "simulate unplug" (TV went
    black, 2026-11-12). The newline ends the token; the padding keeps the 42
    bytes inside our own buffer."""
    fd = os.open(os.path.join(dbg, "trigger_hotplug"), os.O_WRONLY)
    try:
        os.write(fd, b"1\n".ljust(64, b"\0"))
    finally:
        os.close(fd)


def handle(conn_dir):
    """Bring one DP connector's EDID override to the desired state.
    Returns True when it changed something."""
    name = os.path.basename(conn_dir)  # e.g. card0-DP-1
    card, conn = name.split("-", 1)
    dbg = f"/sys/kernel/debug/dri/{card[4:]}/{conn}"
    if not os.path.isdir(dbg):
        log(f"{conn}: no debugfs dir {dbg}, skipping")
        return False
    with open(os.path.join(conn_dir, "status")) as f:
        if f.read().strip() != "connected":
            return False
    aux, i2c = sub_dev(conn_dir, "drm_dp_aux*"), sub_dev(conn_dir, "i2c-*")
    if not aux or not i2c:
        return False
    try:
        oui, dev_id = read_branch(aux)
        raw = read_edid(i2c)
    except OSError as e:
        log(f"{conn}: read failed ({e}), leaving override as is")
        return False
    if raw is None or not valid_edid(raw):
        log(f"{conn}: EDID read invalid, leaving override as is")
        return False
    want = desired_override(raw, oui, dev_id)
    with open(os.path.join(dbg, "edid_override"), "rb") as f:
        have = f.read() or None
    if want == have:
        log(f"{conn}: override already {'FreeSync EDID' if want else 'off'} (branch {oui.hex()} {dev_id!r})")
        return False
    with open(os.path.join(dbg, "edid_override"), "wb") as f:
        f.write(want if want else b"reset")
    trigger_hotplug(dbg)
    log(f"{conn}: override {'set to FreeSync EDID' if want else 'reset'} (branch {oui.hex()} {dev_id!r}), hotplug triggered")
    return True


def main():
    # At boot the connector or debugfs may not exist yet; hotplug events retrigger us.
    for _ in range(30):
        conns = sorted(glob.glob("/sys/class/drm/card*-DP-*"))
        if conns and os.path.isdir("/sys/kernel/debug/dri"):
            break
        time.sleep(1)
    time.sleep(1)  # let the sink settle after a hotplug
    for c in conns:
        try:
            if handle(c):
                time.sleep(3)
                handle(c)  # confirm, and catch an EDID change during the hotplug
        except Exception as e:  # never fail the unit in a way that blocks boot
            log(f"{os.path.basename(c)}: error {e!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
