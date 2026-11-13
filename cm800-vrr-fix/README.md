# VRR fix for the Ugreen CM800 dock

With a TV that lists HDMI VRR in its EDID, the SteamOS kernel (Valve, 7.2.x and later) sends no FreeSync packets through a DP-to-HDMI converter. It leaves HDMI VRR to the converter instead. The CM800 converter (Synaptics, OUI 90-CC-24, ID `cHDMIb`) never turns it on, so the TV gets a fixed 120 Hz with no VRR.

The fix overrides the EDID in the kernel (debugfs `edid_override`) with a copy of the TV's live EDID, with VRRmin and VRRmax zeroed in the HDMI Forum block. The driver then falls back to FreeSync, which this dock passes through. Diagnosed 2026-11-12: the TV showed "VRR on" in Game Mode and on the desktop.

The override is set only when:
- the dock is a CM800 (read from DPCD 0x500 and 0x503),
- the TV's EDID read over DDC has valid checksums,
- the TV has both HDMI VRR and FreeSync (the AMD block). Without FreeSync, VRR would go away completely.

With another display or dock, the service removes the override.

## Files

| File on the system | Role |
|---|---|
| `/etc/cm800-vrr-fix/cm800_vrr_fix.py` | the logic, runs as root |
| `/etc/systemd/system/cm800-vrr-fix.service` | runs at boot |
| `/etc/udev/rules.d/99-cm800-vrr-fix.rules` | runs again on every DRM hotplug |
| `/etc/atomic-update.conf.d/cm800-vrr-fix.conf` | list of files a SteamOS update must keep |
| `~/.config/systemd/user/cm800-vrr-fix-check.service` | checks at login that the fix survived |

Source and backup: this directory (`/home` survives updates).

## After a SteamOS update

An update wipes changes in `/etc` except the files on the keep list. An entry in `/etc/atomic-update.conf.d/` is the supported way to keep them. On 2026-11-12 it was checked with a dry run of the same `rsync` filter that `holo-sync-var` uses. Valve may still change this mechanism.

If the fix disappears, `cm800-vrr-fix-check.service` writes `~/CM800-VRR-FIX-WARNING.txt` at login and tries to send a notification (visible only on the desktop). To repair:

```
sudo ~/.local/share/cm800-vrr-fix/install.sh
```

Manual check:

```
~/.local/share/cm800-vrr-fix/check.sh
journalctl -u cm800-vrr-fix.service -b -o cat
sudo ~/.local/share/cm800-vrr-fix/tools/probe.sh
```

`probe.sh` ends with `VERDICT: GREEN` when the driver sends FreeSync at 4K120 with VRR, and `RED` when it falls back to HDMI VRR. In the Steam UI with nothing moving on screen, it takes the packet type from the EDID rule. `tools/vblank_rate.py auto` measures the real GPU refresh rate.

The fix may stop being needed once Valve changes the driver. It is harmless then, because it only forces FreeSync. To remove it:

```
sudo ~/.local/share/cm800-vrr-fix/uninstall.sh
```

## Tests

```
cd ~/.local/share/cm800-vrr-fix && python3 -B -m unittest discover -s tests -v
```

The fixtures are real LG G3 EDIDs (TV on and in standby) and the EDID that turned VRR on on the TV.

## Limitations

- 1080p120 and other modes without DSC: with VRR on, the dock drops the HDMI signal with both packet types. [vrr-guard](../vrr-guard/README.md) turns VRR off in those modes.
- 4K120 with HDR: the TV does not switch to HDR and the picture looks washed out, with or without VRR and with or without this fix. 4K60 with HDR works. This is a limit of the dock path, not of this fix. [hdr-mode-switch](../hdr-mode-switch/README.md) switches to 4K60 when HDR goes on.
- amdgpu's debugfs `trigger_hotplug` must be written as `1` followed by a newline. A bare `1` can be read by the driver as 0, which means "unplug the display". `tools/repro-hotplug-race.sh` guards this (run it with sudo, with the TV on).
