# Pironman5 Development Guide

## Branches

| Branch | Purpose | Notes |
|--------|---------|-------|
| `ups` | Development mainline | All variants: ups, promax, pipower5 |
| `pipower5` | PiPower5 standalone release | Sync from ups periodically |
| `promax` | Pironman 5 Pro Max release | Sync from ups periodically |

## Architecture

```
pironman5
  ├── PMAuto (pm_auto)
  │   ├── SystemAddon     CPU/RAM/storage/IP
  │   ├── FanAddon        PWM/GPIO fan control
  │   ├── OLEDAddon       Display pages, sleep/wake
  │   ├── PiPower5Addon   UPS battery, buzzer, events
  │   ├── WS2812Addon     RGB LED strip
  │   └── ...
  └── PMDashboard (web UI, port 34001)

piPower5
  ├── kernel driver       sysfs at /sys/class/pipower5/pipower5/
  ├── Python library      pipower5 CLI + email
  └── udev rules          event → systemd-run → email
```

## Variants (products.py)

Variants are assembled from modules (variants/modules/*.py). Each module registers peripherals, default config, event mappings.

| Variant | Modules |
|---------|---------|
| ups | core, network_info, history, oled, oled_ups_pages, pwm_fan, sf_rgb_led, pipower5 |
| pipower5 | core, network_info, history, pipower5 |
| promax | core, network_info, history, oled, ws2812, pi5_power_button |

## Install Script (install.sh)

Uses sunfounder-installer framework. Variants installed via:
```bash
curl .../ups/install.sh | bash -s -- --variant <name>
```

PiPower5 standalone reuses pironman5 framework:
- Variant `pipower5` → installs pironman5 + pipower5 plugin
- Detects and removes old `/opt/pipower5/` installation

## Testing

Test devices:
- 192.168.100.232 — promax
- 192.168.100.131 — pipower5 standalone

```bash
# Deploy to test device
/opt/pironman5/venv/bin/pip3 install --force-reinstall --no-cache-dir \
  git+https://github.com/sunfounder/pironman5.git@<branch>
systemctl restart pironman5

# Check peripherals
curl -s http://localhost:34001/api/v1.0/get-device-info
```

## Recalbox port (`recalbox/`)

Fork-only port for Recalbox 11 (Buildroot, read-only rootfs, no systemd,
exFAT share). Kept entirely in `recalbox/` so upstream syncs do not conflict:
do not patch `pironman5/` for Recalbox, adapt at runtime in
`recalbox/pironman5_recalbox.py` instead. See `recalbox/README.md`.

- Install dir `/recalbox/share/pironman5` (`app/`, `lib/`, `config.json`, `logs/`)
- Autostart: marked block in `/recalbox/share/system/custom.sh` (run by `S99custom`)
- Overlay loaded by the firmware from the Pironman 5 HAT EEPROM: no `/boot` change
- Dependencies: `recalbox/requirements-recalbox.txt` (cp311 aarch64, hashes);
  `pm_auto` / `sf_rpi_status` commits pinned in `recalbox/install.sh`

Test device: 10.185.30.144 — Recalbox 11.0-patron-1.1, Pi 5, Pironman 5

```bash
# Deploy a working tree to the Recalbox and (re)install
tar --exclude=.git -czf - . | ssh root@<recalbox> \
  'mkdir -p /tmp/pm5 && tar -xzf - -C /tmp/pm5 && bash /tmp/pm5/recalbox/install.sh'
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
python3 -m pytest recalbox/tests
```
