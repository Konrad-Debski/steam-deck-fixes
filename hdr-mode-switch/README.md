# Mode switch for HDR (Game Mode)

When you turn HDR on in Steam and the current display mode has no working HDR, the service sets a mode from a list of tested modes. It picks the highest resolution, then the highest refresh rate, but never higher than the current ones. If the list has no such mode, nothing changes. When HDR goes off, the mode from before HDR comes back. If you pick another mode by hand while HDR is on, the service leaves it alone.

Software cannot tell whether HDR really works. The kernel and gamescope report HDR on even when the LG G3 behind the CM800 dock shows a washed-out picture. So the working modes come from a hand-tested list, `hdr-mode-switch.conf`. For a new TV or dock, check each mode on the screen and add a line.

How it works: the service watches the root window atom `GAMESCOPE_DISPLAY_HDR_ENABLED`, writes the mode to `~/.config/gamescope/modes.cfg` and sets the atom `GAMESCOPE_DISPLAY_MODE_NUDGE`. Steam does the same when you change the mode in its settings. The previous mode is stored in `~/.local/state/hdr-mode-switch/previous`.

Everything is in `/home`, so a SteamOS update does not remove it. Valve may still change this gamescope mechanism.

Known Steam quirk, not caused by this service: after any switch from 120 Hz to 60 Hz, Steam's frame limit slider shows its minimum (12) if the saved limit was above 60. The real limit does not change.

```
systemctl --user status hdr-mode-switch      # state
journalctl --user -u hdr-mode-switch -o cat  # switches
systemctl --user disable --now hdr-mode-switch && rm ~/.config/systemd/user/hdr-mode-switch.service  # remove
cd ~/.local/share/hdr-mode-switch && python3 -B -m unittest discover -s tests -v  # tests
```
