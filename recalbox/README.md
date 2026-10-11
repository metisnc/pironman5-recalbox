# Technical notes

User documentation: [README.md](../README.md) (English) ·
[README.fr.md](../README.fr.md) (français).

This folder contains everything specific to Recalbox. The `pironman5/`
package at the repository root is the unmodified SunFounder code; it is
adapted to Recalbox at runtime only.

## Files

| File | Role |
|---|---|
| `install.sh` | Install or upgrade; online, from a local copy of the repository, or `--offline <bundle>` |
| `uninstall.sh` | Stop the service, remove the `custom.sh` block, move the installation to a backup folder |
| `pironman5-service.sh` | `start` / `stop` / `restart` / `status`, called by `custom.sh` |
| `pironman5_recalbox.py` | Launcher: runs `pironman5` with the Recalbox adaptations below |
| `pironman5ctl.py` | Settings CLI, used by the Recalbox menu entries and over SSH |
| `pm5r/` | Recalbox integration: live settings, menu entries, OLED overlay, game events |
| `requirements-recalbox.txt` | Pinned wheels with hashes (CPython 3.11, aarch64) |
| `build-offline-bundle.sh` | Downloads the wheels and the pinned `pm_auto` / `sf_rpi_status` sources |
| `tests/` | Unit tests for the launcher (`python3 -m pytest recalbox/tests`) |

## Installed layout

```
/recalbox/share/pironman5/
├── app/            pironman5 package + recalbox/ scripts
├── lib/            pm_auto, sf_rpi_status and the wheels
├── config.json     settings (kept across upgrades)
└── logs/           pironman5.log (1 MB × 3), console.log
/recalbox/share/system/custom.sh    autostart block between markers
/recalbox/share/pironman5-backups/  dated backups, never deleted automatically
```

## Recalbox constraints and how they are handled

| Constraint | Handling |
|---|---|
| Read-only rootfs and `/boot`, `/opt` not writable | Everything under `/recalbox/share`; config path passed to `Pironman5`, log handler replaced by the launcher |
| No systemd | `S99custom` runs `/recalbox/share/system/custom.sh start\|stop` |
| No pip, no compiler | Throwaway venv in `/tmp` (bundled `ensurepip`) used only to run `pip install --target`; prebuilt wheels only |
| `/recalbox/share` is exFAT (no symlinks, no exec bit, `chmod` fails) | No virtualenv: system `python3` with `PYTHONPATH`; pip installs to tmpfs, then plain copy |
| lgpio creates FIFOs in its working directory | Service runs from `/tmp`, `LG_WD=/tmp` |
| `i2c-dev` not auto-loaded | `modprobe i2c-dev` at service start (runtime only) |
| No `lsblk` / `smartctl` | `get_disks_info` replaced by a psutil implementation |
| Power button handled by Recalbox, no `evdev` | `pi5_power_button` peripheral removed; OLED pages rotate on a timer |
| Games must keep priority | Service runs with `nice 10` |

Case model: the Pironman 5 and Pironman 5 Max EEPROMs both read "Pironman 5",
so `install.sh` asks (or takes `--variant base|max`) and writes
`PM5_HOME/variant`; the launcher assembles that upstream product
(`select_variant`), the Max adding the case fan LEDs on GPIO5.

I2C1, SPI0 and the IR receiver are enabled by `sunfounder-pironman5.dtbo`,
shipped by Recalbox in `/boot/overlays` and loaded by the firmware from the
Pironman 5 HAT EEPROM, so no `config.txt` change is required.

## Hardware used

| Device | Bus / pin | Library |
|---|---|---|
| SSD1306 OLED 128×64 | I2C bus 1, address `0x3C` | `smbus2`, Pillow (system) |
| Case fans | GPIO6 (BCM), on/off | `RPi.GPIO` API from `rpi-lgpio` / `lgpio` |
| Case fan LEDs (Max) | GPIO5 (BCM), on/off | same |
| Raspberry Pi 5 fan | kernel `pwm-fan`, read from `/sys/class/thermal/cooling_device0` | — |
| 4 × WS2812 LEDs | SPI0 MOSI (GPIO10), `/dev/spidev0.0` | Adafruit Blinka, `neopixel_spi` |

## Recalbox integration (`pm5r/`)

| Module | Role |
|---|---|
| `settings.py` | Cycled values, labels, translations (FR/EN from `system.language`), atomic `config.json` writes |
| `menu.py` | Entries of *Menu > User scripts* (`/recalbox/share/userscripts/manual`), named after their result |
| `control.py` | In the service: applies `config.json` changes live, OLED confirmations, game page and LED color |
| `es_events.py` | Game start/stop and screensaver (`sleep`) from `/tmp/es_state.inf` |
| `oled.py` | Wraps pm_auto's OLED pages (confirmation overlay) and adds the `game` page |
| `colors.py` | LED color per manufacturer, from `systemlist.xml` |

- EmulationStation lists `userscripts/manual/*.sh` when the submenu opens,
  runs them with `/bin/sh`, and shows only the file name: it has no API for
  custom notifications. Entry names therefore carry the result, apply an
  explicit value (idempotent) and are renamed after every change. Only files
  containing the marker `# pironman5-recalbox menu entry` are touched.
- Names are a fixed part + ` → ` + result; fixed parts differ before the
  arrow, so the alphabetical order of the menu never changes (tested).
- `config.json` is polled every second; only changed keys are passed to
  `Pironman5.update_config()`. Changes to the addons run in pm_auto's asyncio
  loop (`call_soon_threadsafe`). Game colors are applied to the WS2812 addon
  only, never saved.

## Updating dependencies

- `pm_auto` / `sf_rpi_status`: change `PM_AUTO_COMMIT` / `SF_RPI_STATUS_COMMIT`
  in `install.sh`.
- Wheels: update `requirements-recalbox.txt` with versions and sha256 hashes
  of wheels available for `cp311` / `manylinux_2_34_aarch64` or pure Python
  (the file must list the full dependency closure: pip runs with
  `--no-deps --require-hashes`).
- A new Recalbox Python version requires matching wheels and an update of the
  version check in `install.sh`.

Validate every change on a Recalbox: install, reboot, check OLED, LEDs and
fans, run a game, uninstall.
