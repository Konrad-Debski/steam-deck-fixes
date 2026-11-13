# Przełączanie trybu przy HDR (tryb gry)

Gdy włączysz HDR w Steamie, a bieżący tryb ekranu nie ma działającego HDR, usługa ustawia tryb z listy sprawdzonych trybów: najwyższą rozdzielczość, a potem najwyższe odświeżanie, ale nigdy wyższe od obecnych. Rozdzielczości ani odświeżania nie podnosi. Gdy na liście nie ma takiego trybu, nic nie zmienia. Po wyłączeniu HDR wraca do trybu sprzed włączenia. Jeśli w czasie HDR wybierzesz inny tryb ręcznie, usługa go nie zmienia.

Oprogramowanie nie potrafi odczytać, czy HDR naprawdę działa: jądro i gamescope raportują HDR także wtedy, gdy LG G3 za dockiem CM800 pokazuje sprany obraz. Dlatego działające tryby są w ręcznie sprawdzonej liście `hdr-mode-switch.conf`. Nowy telewizor albo dock: sprawdź tryb na ekranie i dopisz linię.

Jak to działa: usługa śledzi atom `GAMESCOPE_DISPLAY_HDR_ENABLED`, zapisuje tryb w `~/.config/gamescope/modes.cfg` i ustawia atom `GAMESCOPE_DISPLAY_MODE_NUDGE`. Steam robi to samo, gdy zmieniasz tryb w ustawieniach. Poprzedni tryb jest w `~/.local/state/hdr-mode-switch/previous`.

Wszystko jest w `/home`, więc aktualizacja SteamOS tego nie usuwa. Valve może jednak zmienić ten mechanizm w gamescope.

```
systemctl --user status hdr-mode-switch      # stan
journalctl --user -u hdr-mode-switch -o cat  # przełączenia
systemctl --user disable --now hdr-mode-switch && rm ~/.config/systemd/user/hdr-mode-switch.service  # usunięcie
cd ~/.local/share/hdr-mode-switch && python3 -B -m unittest discover -s tests -v  # testy
```
