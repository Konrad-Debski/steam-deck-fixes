#!/usr/bin/python3 -I
"""Game Mode: switch the external display to an HDR-capable mode when Steam
turns HDR on, and back to the previous mode when HDR goes off.

Which modes really show HDR cannot be read from software (the kernel and
gamescope report HDR on while the LG G3 behind the CM800 dock shows a washed
out picture at 4K100/120). So the working modes come from a hand-tested list.
"""
import os
import re
import subprocess
import sys

CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hdr-mode-switch.conf")
STATE = os.path.expanduser("~/.local/state/hdr-mode-switch/previous")
MODE_RE = re.compile(r"^(\d+)x(\d+)@(\d+)$")


def _key(mode):
    w, h, r = map(int, MODE_RE.match(mode).groups())
    return (w * h, r)


def parse_conf(text):
    """'Display name:WxH@R' lines -> {display: {modes}}."""
    ok = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name, mode = line.rsplit(":", 1)
        if MODE_RE.match(mode.strip()):
            ok.setdefault(name.strip(), set()).add(mode.strip())
    return ok


def best_hdr_mode(ok_modes, available, current):
    """Highest resolution, then highest refresh, among tested modes the display
    offers whose width, height and refresh do not exceed the current mode."""
    def parts(mode):
        return tuple(map(int, MODE_RE.match(mode).groups()))
    cur = parts(current)
    usable = [m for m in set(ok_modes) & set(available)
              if all(a <= b for a, b in zip(parts(m), cur))]
    return max(usable, key=_key) if usable else None


def decide(hdr_on, display, current, previous, ok_modes, available):
    """Return (mode to set or None, new previous mode or None).
    previous: the mode to restore after HDR, saved when we switched."""
    if hdr_on:
        if current in ok_modes or current is None:
            return None, previous
        target = best_hdr_mode(ok_modes, available, current)
        if target is None:
            return None, previous
        return target, previous or current
    if previous is None:
        return None, None
    # Restore only if the user did not pick another mode while HDR was on.
    if current in ok_modes and previous in available:
        return previous, None
    return None, None


# --- Session side ------------------------------------------------------------

def x(*args):
    return subprocess.run(["xprop", "-root", *args], capture_output=True, text=True).stdout


def atom(name):
    m = re.search(r"= (.*)$", x(name).strip())
    return m.group(1).strip('"') if m else None


def display_name():
    out = subprocess.run(["gamescopectl"], capture_output=True, text=True).stdout
    make = re.search(r"Display Make: (.*)", out)
    model = re.search(r"Display Model: (.*)", out)
    return f"{make.group(1).strip()} {model.group(1).strip()}" if make and model else None


def read_modes_cfg(path):
    """{display: (mode, rest of line)}; gamescope's format is 'name:WxH@R flags'."""
    out = {}
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r"^(.*):(\d+x\d+@\d+)(.*)$", line.rstrip("\n"))
                if m:
                    out[m.group(1)] = (m.group(2), m.group(3))
    except FileNotFoundError:
        pass
    return out


def set_mode(path, display, mode):
    cfg = read_modes_cfg(path)
    cfg[display] = (mode, cfg.get(display, (None, " 0"))[1])
    with open(path + ".tmp", "w") as f:
        f.writelines(f"{d}:{m}{rest}\n" for d, (m, rest) in cfg.items())
    os.replace(path + ".tmp", path)
    # Same signal Steam sends after it writes this file: gamescope re-reads it.
    x("-f", "GAMESCOPE_DISPLAY_MODE_NUDGE", "32c", "-set", "GAMESCOPE_DISPLAY_MODE_NUDGE", "1")


def read_previous(display):
    try:
        with open(STATE) as f:
            d, mode = f.read().strip().rsplit(":", 1)
        return mode if d == display else None
    except (FileNotFoundError, ValueError):
        return None


def write_previous(display, mode):
    if mode is None:
        if os.path.exists(STATE):
            os.remove(STATE)
        return
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        f.write(f"{display}:{mode}\n")


def on_hdr(hdr_on, modes_cfg):
    if atom("GAMESCOPE_DISPLAY_IS_EXTERNAL") != "1":
        return
    display = display_name()
    try:
        with open(CONF) as f:
            ok = parse_conf(f.read()).get(display, set())
    except FileNotFoundError:
        ok = set()
    if not display or not ok:
        return
    current = read_modes_cfg(modes_cfg).get(display, (None,))[0]
    available = (atom("GAMESCOPE_DISPLAY_MODE_LIST_EXTERNAL") or "").split()
    mode, previous = decide(hdr_on, display, current, read_previous(display), ok, available)
    write_previous(display, previous)
    if mode:
        set_mode(modes_cfg, display, mode)
        print(f"HDR {'on' if hdr_on else 'off'}: {display} {current} -> {mode}", flush=True)


def main():
    modes_cfg = os.environ.get("GAMESCOPE_MODE_SAVE_FILE", os.path.expanduser("~/.config/gamescope/modes.cfg"))
    spy = subprocess.Popen(["xprop", "-spy", "-root", "GAMESCOPE_DISPLAY_HDR_ENABLED"],
                           stdout=subprocess.PIPE, text=True)
    last = None
    for line in spy.stdout:
        m = re.search(r"= (\d+)", line)
        if not m or m.group(1) == last:
            continue
        last = m.group(1)
        try:
            on_hdr(last == "1", modes_cfg)
        except Exception as e:  # keep watching; one bad read must not stop the service
            print(f"error: {e!r}", flush=True)
    return spy.wait()  # gamescope went away; systemd restarts us


if __name__ == "__main__":
    sys.exit(main())
