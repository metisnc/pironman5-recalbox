# Pironman 5 on Recalbox

Runs the SunFounder Pironman 5 service (OLED screen, case fans, RGB LEDs) on
**Recalbox 11 / Raspberry Pi 5**, without modifying `/boot`, the rootfs or the
upstream Python code.

Tested on Recalbox `11.0-patron-1.1`, Raspberry Pi 5 (8 GB, NVMe), Pironman 5
(HAT EEPROM `product_id 0x0132`).

## What works

| Feature | How |
|---|---|
| OLED (SSD1306, I2C bus 1, 0x3C) | pages `mix`, `performance`, `ips`, `disk`, rotating every `oled_page_interval` seconds (10 by default) |
| Case fans (GPIO6) | follow the Pi 5 fan level, default mode *Performance* (on from ~50 °C) |
| Pi 5 fan header | driven by the Recalbox kernel (`pwm-fan`), read by the service |
| RGB LEDs (4 × WS2812, SPI0) | styles `solid`, `breathing`, `flow`, `rainbow`, `hue_cycle`… |

Not included: web dashboard / InfluxDB history, PiPower 5, Pi 5 power button
handling (Recalbox already handles the button), disk temperatures (no
`smartctl`).

## Requirements

- Recalbox 11 on a Raspberry Pi 5 inside a Pironman 5 case.
- Nothing to enable in `/boot`: the Pi 5 firmware reads the Pironman 5 HAT
  EEPROM and loads `sunfounder-pironman5.dtbo` (shipped with Recalbox), which
  enables I2C1, SPI0 and the IR receiver.
- Internet on the Recalbox, or an offline bundle (see below).
- SSH access as root (see the Recalbox documentation for the credentials).

## Install

From a computer, copy the repository to the Recalbox and run the installer:

```bash
scp -r pironman5-recalbox root@recalbox.local:/tmp/
ssh root@recalbox.local 'bash /tmp/pironman5-recalbox/recalbox/install.sh'
```

or directly on the Recalbox:

```bash
wget -qO- https://raw.githubusercontent.com/metisnc/pironman5-recalbox/v1/recalbox/install.sh | bash
```

The installer:

1. backs up `/boot/config.txt`, `/boot/recalbox-user-config.txt`,
   `custom.sh` and `config.json` to `/recalbox/share/pironman5-backups/<date>/`;
2. downloads `pm_auto` and `sf_rpi_status` (pinned commits) and the Python
   wheels listed in `requirements-recalbox.txt` (pinned versions and hashes,
   prebuilt aarch64 wheels only, no compiler needed);
3. installs everything in `/recalbox/share/pironman5/`;
4. adds an autostart block to `/recalbox/share/system/custom.sh`;
5. starts the service.

Running it again upgrades in place; the previous version is kept in the
backup folder. A `/recalbox/share/pironman5` folder from another manual port
is moved to the backup folder and its `config.json` is reused.

### Offline install

On a computer with Internet (macOS or Linux, Python 3 + pip):

```bash
bash recalbox/build-offline-bundle.sh /tmp/pironman5-offline
scp -r /tmp/pironman5-offline pironman5-recalbox root@recalbox.local:/recalbox/share/
ssh root@recalbox.local 'bash /recalbox/share/pironman5-recalbox/recalbox/install.sh --offline /recalbox/share/pironman5-offline'
```

## Usage

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh restart
```

Settings: edit `/recalbox/share/pironman5/config.json` (same keys as the
upstream `pironman5` config, e.g. `rgb_color`, `rgb_style`, `oled_pages`,
`oled_sleep_timeout`, `gpio_fan_mode`), then restart the service.

`oled_page_interval` (Recalbox only): seconds between OLED pages, `0` to
stay on the first page. Upstream changes page with the Pi 5 power button,
which this port leaves to Recalbox. Pages only rotate while the screen is
awake. Keep `oled_sleep_timeout` at `0` (the Recalbox default): without the
power button nothing wakes the screen up once it sleeps.

`gpio_fan_mode`: `0` always on, `1` performance, `2` cool, `3` balanced,
`4` quiet (case fans on when the Pi 5 fan level is >= the mode).

Logs: `/recalbox/share/pironman5/logs/pironman5.log` (1 MB, 2 rotations) and
`console.log` (output of the last start).

## Uninstall / rollback

```bash
bash /recalbox/share/pironman5/app/recalbox/uninstall.sh
```

Stops the service (OLED, LEDs and case fans are switched off), removes the
autostart block from `custom.sh` and moves `/recalbox/share/pironman5` to
`/recalbox/share/pironman5-backups/uninstall-<date>/`. Nothing is deleted:
remove `/recalbox/share/pironman5-backups` by hand when you no longer need it.
To get your settings back after reinstalling, copy
`pironman5-backups/uninstall-<date>/pironman5/config.json` to
`/recalbox/share/pironman5/` and restart the service.
A previous manual port moved aside by the installer is in
`pironman5-backups/<date>/previous-pironman5/` and can be moved back.

## How it works

| File | Role |
|---|---|
| `install.sh` / `uninstall.sh` | install, upgrade, rollback |
| `pironman5-service.sh` | `start`/`stop`/`restart`/`status`, called by `custom.sh` |
| `pironman5_recalbox.py` | launcher: runs the unmodified upstream `pironman5` package with Recalbox adaptations |
| `requirements-recalbox.txt` | pinned wheels (smbus2, rpi-lgpio/lgpio, Adafruit Blinka, neopixel-spi) |
| `build-offline-bundle.sh` | prepares wheels and sources for an offline install |

Recalbox specifics handled by the launcher and service script:

- `/opt` is read-only: config and logs live in `/recalbox/share/pironman5`.
- `/recalbox/share` is exFAT (no symlinks, no exec bit): no virtualenv;
  dependencies are installed with `pip --target` from a throwaway venv in
  `/tmp`, and the service runs the system `python3` with `PYTHONPATH`.
- lgpio creates FIFOs in its working directory: the service runs from `/tmp`.
- `i2c-dev` is not auto-loaded: `modprobe i2c-dev` at start (runtime only).
- No `lsblk`: disk usage is computed with psutil.
- No systemd: started by `S99custom` → `custom.sh`, with `nice 10` so games
  keep priority.

## After a Recalbox upgrade

Upgrades replace the system image but keep `/recalbox/share`, so the
installation and the `custom.sh` block survive. `S99custom` (which runs
`custom.sh`) is part of Recalbox. After an upgrade, check:

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
```

It warns if `S99custom` or the autostart block is missing, or if
`/dev/i2c-1` / `/dev/spidev0.0` are absent. If the Python version of Recalbox
changes (the wheels target CPython 3.11), the installer refuses to run and
the service fails to start: update `requirements-recalbox.txt` and reinstall.

## Known limitations

- Only the Pironman 5 (base) variant is supported (Mini/Max/Pro Max untested).
- Disk temperatures are not shown (no `smartctl` on Recalbox).
- If you enable Recalbox `hat.wpaf` or GPIO controllers
  (`controllers.gpio`), they may conflict with the OLED (I2C1), the case fans
  (GPIO6) or the LEDs (GPIO10/SPI0).
- The IR receiver (GPIO13) is enabled by the overlay but not used by this port.
