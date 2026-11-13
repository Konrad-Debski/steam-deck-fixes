#!/usr/bin/python3 -I
"""Game Mode: keep VRR off in display modes where the dock loses the signal.

The Ugreen CM800 drops HDMI with VRR on in modes sent without DSC
(1080p120, 4K30, ...), with and without the cm800-vrr-fix (TV-checked
2026-11-13). VRR is allowed only in modes listed in vrr-guard.conf. Steam's
own VRR setting (root atom GAMESCOPE_VRR_ENABLED) is left as is; the guard
overrides gamescope's adaptive_sync convar and hands it back on a listed mode.
"""
import os
import re
import subprocess
import sys

CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vrr-guard.conf")
WATCH = ["GAMESCOPE_VRR_ENABLED", "GAMESCOPE_DISPLAY_MODE_LIST_EXTERNAL",
         "GAMESCOPE_DISPLAY_REFRESH_RATE_FEEDBACK", "GAMESCOPE_DISPLAY_IS_EXTERNAL"]


def parse_conf(text):
    """'Display name:WxH@R' lines -> {display: {modes}}."""
    ok = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            name, mode = line.rsplit(":", 1)
            if re.fullmatch(r"\d+x\d+@\d+", mode.strip()):
                ok.setdefault(name.strip(), set()).add(mode.strip())
    return ok


def adaptive_sync(steam_vrr, external, display, mode, conf):
    """Value for gamescope's adaptive_sync: Steam's setting, or 0 in an unlisted
    mode of a display that has a list."""
    if steam_vrr and external and display in conf and mode not in conf[display]:
        return 0
    return 1 if steam_vrr else 0


# --- Session side ------------------------------------------------------------

def atom(name):
    out = subprocess.run(["xprop", "-root", name], capture_output=True, text=True).stdout
    m = re.search(r"= (.*)$", out.strip())
    return m.group(1).strip('"') if m else None


def display_name():
    out = subprocess.run(["gamescopectl"], capture_output=True, text=True).stdout
    make = re.search(r"Display Make: (.*)", out)
    model = re.search(r"Display Model: (.*)", out)
    return f"{make.group(1).strip()} {model.group(1).strip()}" if make and model else None


def current_mode(modes_cfg, display):
    try:
        with open(modes_cfg) as f:
            for line in f:
                m = re.match(r"^(.*):(\d+x\d+@\d+)", line)
                if m and m.group(1) == display:
                    return m.group(2)
    except FileNotFoundError:
        pass
    return None


def check(modes_cfg, last):
    try:
        with open(CONF) as f:
            conf = parse_conf(f.read())
    except FileNotFoundError:
        conf = {}
    display = display_name()
    mode = current_mode(modes_cfg, display)
    want = adaptive_sync(atom("GAMESCOPE_VRR_ENABLED") == "1",
                         atom("GAMESCOPE_DISPLAY_IS_EXTERNAL") == "1", display, mode, conf)
    if want != last:
        subprocess.run(["gamescopectl", "adaptive_sync", str(want)], capture_output=True)
        # gamescope applies VRR on the next frame; a still Steam UI may not paint one.
        subprocess.run(["gamescopectl", "debug_force_repaint"], capture_output=True)
        print(f"{display} {mode}: adaptive_sync {want}", flush=True)
    return want


def main():
    modes_cfg = os.environ.get("GAMESCOPE_MODE_SAVE_FILE", os.path.expanduser("~/.config/gamescope/modes.cfg"))
    spy = subprocess.Popen(["xprop", "-spy", "-root", *WATCH], stdout=subprocess.PIPE, text=True)
    last = None
    for line in spy.stdout:
        if line.startswith("GAMESCOPE_VRR_ENABLED"):
            last = None  # Steam wrote its VRR setting; gamescope may have reset the convar
        try:
            last = check(modes_cfg, last)
        except Exception as e:  # keep watching; one bad read must not stop the service
            print(f"error: {e!r}", flush=True)
    return spy.wait()  # gamescope went away; systemd restarts us


if __name__ == "__main__":
    sys.exit(main())
