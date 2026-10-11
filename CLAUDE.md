# Pironman 5 for Recalbox: development guide

Recalbox-dedicated fork of [sunfounder/pironman5](https://github.com/sunfounder/pironman5).
User docs: `README.md` (EN), `README.fr.md` (FR). Technical notes: `recalbox/README.md`.

## Repository

| Path | Owner | Rule |
|---|---|---|
| `pironman5/` | SunFounder upstream | Do not modify: adapt at runtime in `recalbox/pironman5_recalbox.py` |
| `recalbox/` | this fork | All Recalbox code, scripts, tests and technical notes |
| `README.md`, `README.fr.md` | this fork | Keep both languages in sync |

Branches: `v1` (release, installer URL points to it), `recalbox-port`
(development). Never commit directly to `v1`: merge `recalbox-port` with
`--no-ff`.

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

## Syncing with SunFounder

```bash
git remote add upstream https://github.com/sunfounder/pironman5.git  # once
git fetch upstream
git switch recalbox-port
git merge upstream/v1
```

Files removed in this fork (Raspberry Pi OS installer, Docker, scripts,
overlays, upstream tests, docs) come back as modify/delete conflicts: keep
them deleted with `git rm <path>`. Only `pironman5/` changes are relevant:
check that `recalbox/pironman5_recalbox.py` still matches the upstream API
(`Pironman5(config_path=...)`, `variants.PERIPHERALS`, `pm_auto` addons),
then test on a Recalbox before merging into `v1`.
