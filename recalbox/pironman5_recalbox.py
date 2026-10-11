#!/usr/bin/env python3
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Run the unmodified pironman5 service on Recalbox.

Recalbox has a read-only rootfs, no systemd, no lsblk and keeps persistent
data on an exFAT partition. Instead of patching the upstream package, this
launcher adapts it at runtime:

- config and logs live in PM5_HOME (default /recalbox/share/pironman5)
- the Pi 5 power button addon is dropped (Recalbox already handles the
  button, and evdev is not available)
- disk usage is computed with psutil instead of lsblk
- OLED pages rotate automatically (upstream only changes page with the
  power button)
- Recalbox integration (pm5r): settings changed live from the Recalbox menu,
  OLED confirmations, "now playing" page and LED color per console
"""
import json
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

PM5_HOME = os.environ.get('PM5_HOME', '/recalbox/share/pironman5')
CONFIG_PATH = os.path.join(PM5_HOME, 'config.json')
LOG_DIR = os.path.join(PM5_HOME, 'logs')
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 2

# Peripherals of the "base" variant that cannot work on Recalbox
EXCLUDED_PERIPHERALS = ['pi5_power_button']

# Recalbox-specific defaults, applied only when no config file exists yet
RECALBOX_DEFAULT_CONFIG = {
    'system': {
        'gpio_fan_mode': 1,  # Performance: case fans follow the Pi 5 fan
        'enable_history': False,
        'oled_page_interval': 10,
        # Nothing wakes the screen up without the power button addon
        'oled_sleep_timeout': 0,
    },
}
OLED_PAGE_INTERVAL_DEFAULT = 10  # seconds, 0 disables the rotation


def _partition_of(device_name, disk_name):
    """True if device_name is disk_name itself or one of its partitions."""
    if device_name == disk_name:
        return True
    if not device_name.startswith(disk_name):
        return False
    suffix = device_name[len(disk_name):]
    if suffix.startswith('p'):
        suffix = suffix[1:]
    return suffix.isdigit()


def get_disks_info(disks=None, temperature=False):
    """psutil based replacement for sf_rpi_status.get_disks_info (no lsblk)."""
    import psutil
    from sf_rpi_status import get_disks, get_disk_type, DiskInfo

    if disks is None:
        disks = get_disks()
    partitions = psutil.disk_partitions(all=False)
    disk_info = {}
    for disk in sorted(disks):
        name = os.path.basename(disk)
        total = used = free = 0
        mounted = False
        counted = set()
        for partition in partitions:
            device = partition.device
            if not _partition_of(os.path.basename(device), name):
                continue
            mounted = True
            # A partition can be mounted several times (share, bind mounts)
            if device in counted:
                continue
            counted.add(device)
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except OSError:
                continue
            total += usage.total
            used += usage.used
            free += usage.free
        if not mounted:
            try:
                with open(f'/sys/class/block/{name}/size') as f:
                    total = int(f.read()) * 512
            except (OSError, ValueError):
                continue
        if total == 0:
            continue
        percent = round(used / total * 100, 2) if mounted else 0.0
        disk_info[disk] = DiskInfo(
            total=total,
            used=used,
            free=free,
            percent=percent,
            path=disk,
            mounted=mounted,
            temperature=None,
            type=get_disk_type(disk),
        )
    return disk_info


def write_default_config():
    if os.path.exists(CONFIG_PATH):
        return
    with open(CONFIG_PATH, 'w') as f:
        json.dump(RECALBOX_DEFAULT_CONFIG, f, indent=4)


def redirect_log(log):
    """Replace the /var/log (RAM) handlers with a small rotating file in PM5_HOME."""
    formatter = None
    for handler in list(log.handlers):
        if isinstance(handler, RotatingFileHandler):
            formatter = handler.formatter
        log.removeHandler(handler)
        handler.close()
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'pironman5.log'),
        maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    file_handler.setLevel(log.level)
    file_handler.setFormatter(formatter or logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
        datefmt='%y/%m/%d %H:%M:%S'))
    log.addHandler(file_handler)


def next_oled_page(app):
    """Show the next OLED page, unless the screen is asleep."""
    oled = app.pm_auto.addons.addons.get('oled')
    # Publishing while asleep would wake the screen and defeat the sleep timeout
    if oled is not None and oled.wake_flag:
        app.pm_auto.event.publish('oled_wake_page_next')


def page_interval(app):
    interval = app.config['system'].get('oled_page_interval', OLED_PAGE_INTERVAL_DEFAULT)
    if not isinstance(interval, (int, float)) or interval <= 0:
        return None
    return interval


def stop_with_pm_auto(app, stop):
    """Run stop() before PMAuto stops, so Pironman5.stop() finds no thread left."""
    pm_auto_stop = app.pm_auto.stop

    def stop_all():
        stop()
        pm_auto_stop()

    app.pm_auto.stop = stop_all


def start_oled_page_rotation(app):
    stopping = threading.Event()

    def rotate():
        # Interval read each time: it can be changed while running
        while not stopping.wait(page_interval(app) or 1):
            if page_interval(app):
                next_oled_page(app)

    thread = threading.Thread(target=rotate, name='oled-page-rotation', daemon=True)
    thread.start()

    def stop():
        stopping.set()
        thread.join()

    stop_with_pm_auto(app, stop)


def start_recalbox_integration(app, log):
    """Live settings, OLED confirmations, game page and LED colors (pm5r)."""
    from pm5r import oled
    from pm5r.control import Integration

    integration = Integration(app, log, config_path=CONFIG_PATH)
    oled.install(integration.toast, lambda: integration.games.game)
    integration.start()
    stop_with_pm_auto(app, integration.stop)
    return integration


def select_variant(variants, key):
    """Assemble the pironman5 product `key` (upstream reads /opt/pironman5/.variant).

    Must run before pironman5.pironman5 is imported: it copies NAME, ID and
    PRODUCT_VERSION at import time. Lists and dicts are updated in place.
    """
    from pironman5.variants.modules import assemble
    from pironman5.variants.products import PRODUCT_DEFINITIONS

    product = PRODUCT_DEFINITIONS[key]
    assembled = assemble(product['modules'])
    variants.PERIPHERALS[:] = assembled['peripherals']
    variants.SYSTEM_DEFAULT_CONFIG.clear()
    variants.SYSTEM_DEFAULT_CONFIG.update(assembled['default_config'])
    variants.SYSTEM_DEFAULT_CONFIG.update(product.get('config_overrides', {}))
    variants.EVENT_MAP.clear()
    variants.EVENT_MAP.update(assembled['event_map'])
    variants.EVENT_MAP.update(product.get('event_map_overrides', {}))
    variants.NAME = product['name']
    variants.ID = product['id']
    variants.PRODUCT_VERSION = product['product_version']
    variants.VARIENT = key


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    # The upstream logger opens /var/log/pironman5/pironman5.log at import time
    os.makedirs('/var/log/pironman5', exist_ok=True)
    write_default_config()

    from pironman5 import variants
    from pm5r import settings
    select_variant(variants, settings.variant(PM5_HOME))
    for peripheral in EXCLUDED_PERIPHERALS:
        while peripheral in variants.PERIPHERALS:
            variants.PERIPHERALS.remove(peripheral)
    for name in list(variants.EVENT_MAP):
        if name.startswith(tuple(EXCLUDED_PERIPHERALS)):
            del variants.EVENT_MAP[name]

    import pm_auto.addons.system as system_addon
    system_addon.get_disks_info = get_disks_info

    from pironman5 import pironman5 as service
    redirect_log(service.log)
    service.log.info('Recalbox launcher: PM5_HOME=%s', PM5_HOME)

    from pm5r.control import patch_fan_addon
    patch_fan_addon()  # before the addons are created
    app = service.Pironman5(config_path=CONFIG_PATH)
    start_oled_page_rotation(app)
    start_recalbox_integration(app, service.log)
    app.start()


if __name__ == '__main__':
    sys.exit(main())
