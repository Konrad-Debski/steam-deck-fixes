# VRR guard (Game Mode)

The Ugreen CM800 dock drops the HDMI signal when VRR is on in a mode sent without DSC compression (1080p 120 Hz, 4K 30 Hz and below). This happens with and without `cm800-vrr-fix` (checked on the TV 2026-11-13).

The service watches the display mode and Steam's VRR setting. In a mode that is not listed in `vrr-guard.conf`, it turns VRR off in gamescope (`gamescopectl adaptive_sync 0`). In a listed mode, it hands control back to Steam's setting. The VRR toggle in Steam stays on even though VRR is not running. This is on purpose: VRR comes back by itself when you return to 4K.

The LG TV may still show "FreeSync Premium", because the dock still reports FreeSync support. Whether VRR really runs shows in a game as a changing refresh rate.

The list holds the modes where the kernel uses DSC (debugfs `dsc_bits_per_pixel` not 0, measured 2026-11-13). VRR checked on the TV: 4K 120 Hz and 4K 60 Hz.

```
systemctl --user status vrr-guard
journalctl --user -u vrr-guard -o cat
cd ~/.local/share/vrr-guard && python3 -B -m unittest discover -s tests -v
systemctl --user disable --now vrr-guard && rm ~/.config/systemd/user/vrr-guard.service  # remove
```

Everything is in `/home`, so a SteamOS update does not remove it.
