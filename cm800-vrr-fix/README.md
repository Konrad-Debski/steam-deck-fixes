# Poprawka VRR dla docka Ugreen CM800

Jądro SteamOS (Valve, od 7.2.x) przy telewizorze z HDMI VRR w EDID nie wysyła pakietów FreeSync przez konwerter DP-HDMI. Zostawia włączenie HDMI VRR konwerterowi. Konwerter w CM800 (Synaptics, OUI 90-CC-24, ID `cHDMIb`) tego nie robi, więc TV dostaje stałe 120 Hz bez VRR.

Poprawka nadpisuje EDID w jądrze (debugfs `edid_override`) kopią bieżącego EDID telewizora z wyzerowanym VRRmin/VRRmax w bloku HDMI Forum. Sterownik wraca wtedy do FreeSync, który ten dock przepuszcza. Diagnoza z 2026-11-12: TV pokazywał „VRR on” w trybie gry i na pulpicie.

Nadpisanie jest ustawiane tylko wtedy, gdy:
- dock to CM800 (odczyt DPCD 0x500 i 0x503),
- EDID telewizora odczytany przez DDC ma poprawne sumy kontrolne,
- TV ma zarówno HDMI VRR, jak i FreeSync (blok AMD). Bez FreeSync VRR zniknąłby całkiem.

Inny ekran albo inny dock: usługa zdejmuje nadpisanie.

## Pliki

| Plik w systemie | Rola |
|---|---|
| `/etc/cm800-vrr-fix/cm800_vrr_fix.py` | logika, uruchamiana jako root |
| `/etc/systemd/system/cm800-vrr-fix.service` | start przy uruchomieniu systemu |
| `/etc/udev/rules.d/99-cm800-vrr-fix.rules` | ponowne sprawdzenie przy każdym hotplugu DRM |
| `/etc/atomic-update.conf.d/cm800-vrr-fix.conf` | lista plików, które aktualizacja SteamOS ma zachować |
| `~/.config/systemd/user/cm800-vrr-fix-check.service` | po starcie sprawdza, czy poprawka przetrwała |

Źródło i kopia zapasowa: ten katalog (`/home` przetrwa aktualizację).

## Po aktualizacji SteamOS

Aktualizacja kasuje zmiany w `/etc` poza listą zachowywanych plików. Wpis w `/etc/atomic-update.conf.d/` jest oficjalnym sposobem, żeby je zachować, i 2026-11-12 sprawdziłem go na sucho tym samym filtrem `rsync`, którego używa `holo-sync-var`. Valve może jednak zmienić ten mechanizm.

Jeśli poprawka zniknie, `cm800-vrr-fix-check.service` przy starcie zapisze `~/CM800-VRR-FIX-UWAGA.txt` i spróbuje wysłać powiadomienie (widać je tylko na pulpicie). Naprawa:

```
sudo ~/.local/share/cm800-vrr-fix/install.sh
```

Ręczne sprawdzenie:

```
~/.local/share/cm800-vrr-fix/check.sh
journalctl -u cm800-vrr-fix.service -b -o cat
sudo ~/.local/share/cm800-vrr-fix/tools/probe.sh
```

`probe.sh` kończy się `VERDICT: GREEN`, gdy sterownik wysyła FreeSync przy 4K120 z VRR, a `RED`, gdy wraca do HDMI VRR. W interfejsie Steam bez ruchu na ekranie typ pakietu bierze z reguły EDID. `tools/vblank_rate.py auto` mierzy rzeczywiste odświeżanie GPU.

Poprawka może przestać być potrzebna, gdy Valve zmieni sterownik. Jest wtedy nieszkodliwa, bo wymusza tylko FreeSync. Usunięcie:

```
sudo ~/.local/share/cm800-vrr-fix/uninstall.sh
```

## Testy

```
cd ~/.local/share/cm800-vrr-fix && python3 -B -m unittest discover -s tests -v
```

Fixture'y to prawdziwe EDID-y LG G3 (włączony i w czuwaniu) oraz EDID, który na TV włączył VRR.

## Ograniczenia

- 1080p120 i inne tryby bez DSC: z VRR dock gubi sygnał HDMI przy obu rodzajach pakietu. Wyjście trzymaj na 3840×2160.
- 4K120 z HDR: TV nie przechodzi w HDR i obraz jest sprany, z VRR i bez, z poprawką i bez niej. 4K60 z HDR działa. To ograniczenie toru z dockiem, nie tej poprawki.
- `trigger_hotplug` w debugfs amdgpu trzeba zapisywać jako `1` ze znakiem nowej linii. Samo `1` sterownik potrafi odczytać jako 0, czyli „odłącz ekran”. Pilnuje tego `tools/repro-hotplug-race.sh` (uruchamiać przez sudo, przy włączonym TV).
