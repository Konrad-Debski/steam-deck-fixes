# Poprawki dla Steam Decka

Poprawki obrazu dla Steam Decka LCD z dockiem Ugreen CM800 i telewizorem LG OLED G3 (HDMI 2.1). Sprawdzone na SteamOS 3.9 z jądrem 7.2.7-valve2.

| Katalog | Co robi |
|---|---|
| [cm800-vrr-fix](cm800-vrr-fix/README.md) | Włącza VRR przez dock: jądro wysyła FreeSync zamiast HDMI VRR, którego konwerter w docku nie obsługuje. Usługa systemowa w `/etc`, chroniona przed aktualizacją SteamOS. |
| [hdr-mode-switch](hdr-mode-switch/README.md) | Po włączeniu HDR przełącza na sprawdzony tryb z działającym HDR, nie wyższy od obecnego. Po wyłączeniu HDR wraca do poprzedniego trybu. |
| [vrr-guard](vrr-guard/README.md) | Wyłącza VRR w trybach bez DSC, w których dock gubi sygnał (1080p, 4K 30 Hz i niższe). |

Kod jest pod `~/steam-deck-fixes`, a `~/.local/share/<katalog>` to dowiązania do niego. Z tych ścieżek korzystają usługi.

## Instalacja

```
ln -s ~/steam-deck-fixes/{cm800-vrr-fix,hdr-mode-switch,vrr-guard} ~/.local/share/
sudo ~/.local/share/cm800-vrr-fix/install.sh
for s in hdr-mode-switch vrr-guard; do
  ln -sf ~/.local/share/$s/$s.service ~/.config/systemd/user/$s.service
done
systemctl --user daemon-reload
systemctl --user enable --now hdr-mode-switch vrr-guard
```

Listy trybów w `hdr-mode-switch.conf` i `vrr-guard.conf` dotyczą tego konkretnego telewizora i docka. Inny sprzęt wymaga własnych pomiarów.
