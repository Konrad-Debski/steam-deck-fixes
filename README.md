# Steam Deck fixes

Display fixes for a Steam Deck LCD with a Ugreen CM800 dock and an LG OLED G3 TV over HDMI 2.1. Tested on SteamOS 3.9 with kernel 7.2.7-valve2.

| Directory | What it does |
|---|---|
| [cm800-vrr-fix](cm800-vrr-fix/README.md) | Makes VRR work through the dock. The kernel sends FreeSync instead of HDMI VRR, which the dock's converter ignores. A system service in `/etc`, protected from SteamOS updates. |
| [hdr-mode-switch](hdr-mode-switch/README.md) | When HDR goes on, switches to a tested mode where HDR works, never higher than the current mode. When HDR goes off, restores the previous mode. |
| [vrr-guard](vrr-guard/README.md) | Turns VRR off in modes without DSC, where the dock drops the signal (1080p, 4K 30 Hz and below). |

The code lives in `~/steam-deck-fixes`. Each `~/.local/share/<directory>` is a symlink to it, and the services use those paths.

## Install

```
git clone https://github.com/Konrad-Debski/steam-deck-fixes.git ~/steam-deck-fixes
ln -s ~/steam-deck-fixes/{cm800-vrr-fix,hdr-mode-switch,vrr-guard} ~/.local/share/
sudo ~/.local/share/cm800-vrr-fix/install.sh
for s in hdr-mode-switch vrr-guard; do
  ln -sf ~/.local/share/$s/$s.service ~/.config/systemd/user/$s.service
done
systemctl --user daemon-reload
systemctl --user enable --now hdr-mode-switch vrr-guard
```

The mode lists in `hdr-mode-switch.conf` and `vrr-guard.conf` are for this TV and dock only. Other hardware needs its own measurements.
