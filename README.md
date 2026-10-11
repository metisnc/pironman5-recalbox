# Pironman 5 for Recalbox

**English** | [Français](README.fr.md)

Run the [SunFounder Pironman 5](https://www.sunfounder.com/) case features on
[Recalbox](https://www.recalbox.com/): OLED status screen, case fans and RGB
LEDs, on a Raspberry Pi 5.

The official Pironman 5 installer targets Raspberry Pi OS (apt, systemd,
virtualenv in `/opt`, InfluxDB) and cannot run on Recalbox. This project
provides a dedicated installer that keeps everything in the persistent
`/recalbox/share` partition, never modifies `/boot` or the system image, and
survives reboots and Recalbox upgrades.

> This is a community project, not affiliated with SunFounder or Recalbox.

## Contents

- [Features](#features)
- [Compatibility](#compatibility)
- [Installation](#installation)
- [Configuration](#configuration)
- [Service management](#service-management)
- [Uninstallation](#uninstallation)
- [Recalbox upgrades](#recalbox-upgrades)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [How it works](#how-it-works)
- [Credits and license](#credits-and-license)

## Features

| Feature | Details |
|---|---|
| OLED screen | IP addresses (Ethernet and Wi-Fi), CPU load and temperature, RAM, disk usage; pages rotate automatically |
| Case fans | Follow the Raspberry Pi 5 fan: switched on from about 50 °C by default, five modes available |
| RGB LEDs | 4 WS2812 LEDs: solid, breathing, flow, rainbow, hue cycle; color, brightness and speed configurable |
| Raspberry Pi 5 fan | Left to the Recalbox kernel driver, as on a stock system |
| Footprint | About 2 % of one CPU core and 30 MB of RAM, running at low priority so games keep precedence |

## Compatibility

| Component | Supported |
|---|---|
| Recalbox | 11.0 (tested on `11.0-patron-1.1`) |
| Board | Raspberry Pi 5 |
| Case | Pironman 5 |

Not supported: Pironman 5 Mini, Max, Pro Max and NAS, other Raspberry Pi
models.

## Installation

Requirements:

- the Pironman 5 assembled on a Raspberry Pi 5 running Recalbox 11;
- SSH access to the Recalbox as `root` (see the
  [Recalbox documentation](https://wiki.recalbox.com/) for the credentials);
- an Internet connection on the Recalbox, or the
  [offline installation](#offline-installation).

Nothing needs to be enabled in `/boot`: the Raspberry Pi firmware detects the
Pironman 5 and loads its device tree overlay (I2C and SPI) automatically.

### Online installation

Connect to the Recalbox with SSH and run:

```bash
wget -qO- https://raw.githubusercontent.com/metisnc/pironman5-recalbox/v1/recalbox/install.sh | bash
```

The service starts immediately: the OLED screen, the RGB LEDs and the case
fans come on within a few seconds.

The installer:

1. checks the system (Recalbox, Raspberry Pi 5, Python 3.11, Pironman 5);
2. backs up the files it may affect to `/recalbox/share/pironman5-backups/<date>/`;
3. downloads the dependencies, pinned to tested versions and verified by
   checksum (prebuilt packages only, no compiler needed);
4. installs everything in `/recalbox/share/pironman5/`;
5. registers the service in `/recalbox/share/system/custom.sh`, which Recalbox
   runs at startup and shutdown;
6. starts the service.

Running the installer again upgrades the installation and keeps your
settings.

### Offline installation

On a computer with Internet access, Python 3 and Git:

```bash
git clone -b v1 https://github.com/metisnc/pironman5-recalbox.git
bash pironman5-recalbox/recalbox/build-offline-bundle.sh pironman5-offline
scp -r pironman5-recalbox pironman5-offline root@recalbox.local:/recalbox/share/
ssh root@recalbox.local \
  'bash /recalbox/share/pironman5-recalbox/recalbox/install.sh --offline /recalbox/share/pironman5-offline'
```

Replace `recalbox.local` with the address of your Recalbox if needed.

## Configuration

Settings are stored in `/recalbox/share/pironman5/config.json`, which you can
also reach through the Recalbox network share. Edit the values in the
`system` section, then [restart the service](#service-management).

| Key | Values | Default |
|---|---|---|
| `rgb_enable` | `true`, `false` | `true` |
| `rgb_style` | `solid`, `breathing`, `flow`, `flow_reverse`, `rainbow`, `rainbow_reverse`, `hue_cycle` | `breathing` |
| `rgb_color` | hexadecimal color, e.g. `"#0a1aff"` | `"#0a1aff"` |
| `rgb_brightness` | `0` to `100` | `100` |
| `rgb_speed` | `0` to `100` | `50` |
| `oled_enable` | `true`, `false` | `true` |
| `oled_pages` | list of `mix`, `performance`, `ips`, `disk` | all four |
| `oled_page_interval` | seconds between pages, `0` to stay on the first page | `10` |
| `oled_rotation` | `0`, `180` | `0` |
| `oled_sleep_timeout` | seconds before the screen turns off, `0` = never | `0` |
| `temperature_unit` | `C`, `F` | `C` |
| `gpio_fan_mode` | case fans: `0` always on, `1` performance, `2` cool, `3` balanced, `4` quiet | `1` |
| `debug_level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

`gpio_fan_mode` sets the Raspberry Pi 5 fan level from which the case fans
turn on: `1` from about 50 °C, `2` from about 60 °C, `3` from about 67 °C,
`4` from about 75 °C.

Keep `oled_sleep_timeout` at `0`: Recalbox keeps control of the power button,
so nothing wakes the screen up once it has turned off.

## Service management

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh restart
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh stop
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh start
```

Logs are in `/recalbox/share/pironman5/logs/`: `pironman5.log` (limited to
3 MB in total) and `console.log` (output of the last start).

## Uninstallation

```bash
bash /recalbox/share/pironman5/app/recalbox/uninstall.sh
```

The uninstaller stops the service (screen, LEDs and case fans are switched
off), removes the startup entry from `custom.sh` and moves the installation
to `/recalbox/share/pironman5-backups/uninstall-<date>/`. Nothing is deleted:
remove `/recalbox/share/pironman5-backups` yourself once you no longer need
it.

To get your settings back after reinstalling, copy `config.json` from the
backup folder to `/recalbox/share/pironman5/` and restart the service.

## Recalbox upgrades

Recalbox upgrades replace the system image but keep `/recalbox/share`, where
the installation and its startup entry live: the service keeps working
after an upgrade. To check:

```bash
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
```

The command reports a warning if the startup hook or the I2C/SPI devices are
missing. If a future Recalbox release ships a Python version other than 3.11,
the service will not start until a matching release of this project is
installed.

## Troubleshooting

| Symptom | Check |
|---|---|
| Nothing works | `status` above, then `logs/console.log` and `logs/pironman5.log` |
| OLED screen stays black | `cat /proc/device-tree/hat/product` shows `Pironman 5`; `i2cdetect -y 1` shows `3c` |
| RGB LEDs stay off | `ls /dev/spidev0.0`; `rgb_enable` and `rgb_brightness` in `config.json` |
| Case fans never stop | `gpio_fan_mode` is `0` (always on) |
| Settings ignored | `config.json` is valid JSON; restart the service after editing |

## Limitations

- The web dashboard and history (InfluxDB) of the official software are not
  included, to keep the footprint low.
- The Raspberry Pi 5 power button stays under Recalbox control: OLED pages
  rotate automatically instead of changing with the button.
- Disk temperatures are not displayed.
- Enabling the Recalbox `hat.wpaf` fan/OLED support or GPIO controllers
  (`controllers.gpio`) conflicts with this service (shared I2C bus and GPIO
  pins).

## How it works

The service runs the official SunFounder `pironman5` software, unmodified,
through a launcher that adapts it to Recalbox: settings and logs on the share
partition, no systemd, no `lsblk`, exFAT file system. See
[recalbox/README.md](recalbox/README.md) for the technical details.

| Path | Content |
|---|---|
| `pironman5/` | SunFounder `pironman5` package (upstream) |
| `recalbox/` | Recalbox installer, uninstaller, service script and launcher |

## Credits and license

Recalbox port © 2026 metisnc. Based on [sunfounder/pironman5](https://github.com/sunfounder/pironman5),
[pm_auto](https://github.com/sunfounder/pm_auto) and
[sf_rpi_status](https://github.com/sunfounder/sf_rpi_status) by SunFounder.

Licensed under the GNU General Public License v2.0, see [LICENSE](LICENSE)
and [NOTICE](NOTICE).
