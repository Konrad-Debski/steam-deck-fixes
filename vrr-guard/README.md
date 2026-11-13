# Strażnik VRR (tryb gry)

Dock Ugreen CM800 gubi sygnał HDMI, gdy VRR jest włączony w trybie wysyłanym bez kompresji DSC (1080p 120 Hz, 4K 30 Hz i niższe). Dzieje się tak z poprawką `cm800-vrr-fix` i bez niej (sprawdzone na TV 2026-11-13).

Usługa śledzi tryb ekranu i ustawienie VRR w Steamie. W trybie spoza listy `vrr-guard.conf` wyłącza VRR w gamescope (`gamescopectl adaptive_sync 0`). W trybie z listy oddaje sterowanie ustawieniu ze Steama. Przełącznik VRR w Steamie zostaje włączony, choć VRR wtedy nie działa. To zamierzone, bo po powrocie do 4K VRR wraca sam.

Telewizor LG może dalej pokazywać „FreeSync Premium”, bo dock nadal zgłasza obsługę FreeSync. Czy VRR naprawdę działa, widać po zmiennym odświeżaniu w grze.

Na liście są tryby, w których jądro używa DSC (`dsc_bits_per_pixel` w debugfs różne od 0, pomiar 2026-11-13). VRR sprawdzony na TV: 4K 120 Hz i 4K 60 Hz.

```
systemctl --user status vrr-guard
journalctl --user -u vrr-guard -o cat
cd ~/.local/share/vrr-guard && python3 -B -m unittest discover -s tests -v
systemctl --user disable --now vrr-guard && rm ~/.config/systemd/user/vrr-guard.service  # usunięcie
```

Wszystko jest w `/home`, więc aktualizacja SteamOS tego nie usuwa.
