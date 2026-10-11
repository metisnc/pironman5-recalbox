# Pironman 5 for Recalbox: development guide

Recalbox port of [sunfounder/pironman5](https://github.com/sunfounder/pironman5),
maintained independently (see [Upstream policy](#upstream-policy)).
User docs: `README.md` (EN), `README.fr.md` (FR). Technical notes: `recalbox/README.md`.

## Repository

| Path | Owner | Rule |
|---|---|---|
| `pironman5/` | imported from SunFounder | Prefer adapting at runtime in `recalbox/pironman5_recalbox.py` over editing it |
| `recalbox/` | this fork | All Recalbox code, scripts, tests and technical notes |
| `README.md`, `README.fr.md` | this fork | Keep both languages in sync |

Branches: `main-pr5-rc` (release, default branch, installer URL points to
it), `dev-pr5-rc` (development). Never commit directly to `main-pr5-rc`:
merge `dev-pr5-rc` with `--no-ff`.

## Runtime architecture

```
S99custom → /recalbox/share/system/custom.sh → recalbox/pironman5-service.sh
  └── python3 recalbox/pironman5_recalbox.py   (nice 10, cwd /tmp)
        └── pironman5.Pironman5 → pm_auto.PMAuto
              ├── SystemAddon   (sf_rpi_status: CPU, RAM, disks, IPs)
              ├── FanAddon      (Pi 5 kernel fan level → case fans on GPIO6)
              ├── OLEDAddon     (SSD1306, I2C bus 1, 0x3C)
              └── WS2812Addon   (SPI0)
```

Installed in `/recalbox/share/pironman5` (`app/`, `lib/`, `config.json`,
`logs/`). Only the `pironman5` "base" variant (Pironman 5) is supported.

## Checks before committing

```bash
shellcheck recalbox/*.sh
python3 -m py_compile recalbox/*.py pironman5/*.py
python3 -m pytest recalbox/tests
```

The same checks run in GitHub Actions (`.github/workflows/ci.yml`).

## Testing on a Recalbox

```bash
# Copy the working tree and (re)install
tar --exclude=.git -czf - . | ssh root@<recalbox-host> \
  'mkdir -p /tmp/pm5 && tar -xzf - -C /tmp/pm5 && bash /tmp/pm5/recalbox/install.sh'

# On the Recalbox
bash /recalbox/share/pironman5/app/recalbox/pironman5-service.sh status
tail -f /recalbox/share/pironman5/logs/pironman5.log
```

Validate: service starts, survives a reboot, OLED / LEDs / case fans work,
a game runs normally, `uninstall.sh` restores the initial state. Never
modify `/boot` or the rootfs on the test device.

## Upstream policy

This project is maintained independently and is **not synchronized** with
SunFounder: no `upstream` remote, never use GitHub's "Sync fork" and never
merge `sunfounder/pironman5`. `pironman5/` is the code imported at fork time
(version 1.3.20) and is only changed here.

`pm_auto` and `sf_rpi_status` are pinned to fixed commits in
`recalbox/install.sh` (`PM_AUTO_COMMIT`, `SF_RPI_STATUS_COMMIT`): SunFounder
changes never reach installations. Bump a pin only on purpose, after testing
on a Recalbox.
