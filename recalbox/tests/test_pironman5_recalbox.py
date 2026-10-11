# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the Recalbox launcher (run with: python3 -m pytest recalbox/tests)."""
import os
import sys
import types
from collections import namedtuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pironman5_recalbox as launcher  # noqa: E402

Partition = namedtuple('Partition', 'device mountpoint fstype')
Usage = namedtuple('Usage', 'total used free percent')


def test_partition_of():
    assert launcher._partition_of('nvme0n1', 'nvme0n1')
    assert launcher._partition_of('nvme0n1p4', 'nvme0n1')
    assert launcher._partition_of('mmcblk0p2', 'mmcblk0')
    assert launcher._partition_of('sda1', 'sda')
    assert not launcher._partition_of('mmcblk0boot0', 'mmcblk0')
    assert not launcher._partition_of('nvme0n10', 'nvme0n1p')
    assert not launcher._partition_of('sdb1', 'sda')


def _fake_app(oled):
    published = []
    addons = {} if oled is None else {'oled': oled}
    app = types.SimpleNamespace(pm_auto=types.SimpleNamespace(
        addons=types.SimpleNamespace(addons=addons),
        event=types.SimpleNamespace(publish=published.append),
    ))
    return app, published


def test_next_oled_page_only_when_awake():
    app, published = _fake_app(types.SimpleNamespace(wake_flag=True))
    launcher.next_oled_page(app)
    assert published == ['oled_wake_page_next']

    app, published = _fake_app(types.SimpleNamespace(wake_flag=False))
    launcher.next_oled_page(app)
    assert published == []

    app, published = _fake_app(None)  # OLED not detected
    launcher.next_oled_page(app)
    assert published == []


def test_get_disks_info_counts_each_partition_once(monkeypatch):
    # Recalbox mounts the share partition several times
    partitions = [
        Partition('/dev/nvme0n1p1', '/boot', 'vfat'),
        Partition('/dev/nvme0n1p4', '/var/recalboxfs', 'exfat'),
        Partition('/dev/nvme0n1p4', '/recalbox/share', 'exfat'),
        Partition('/dev/loop0', '/overlay/lower', 'squashfs'),
    ]
    usages = {
        '/boot': Usage(100, 10, 90, 10.0),
        '/var/recalboxfs': Usage(1000, 500, 500, 50.0),
        '/recalbox/share': Usage(1000, 500, 500, 50.0),
    }

    class DiskInfo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    psutil = types.SimpleNamespace(
        disk_partitions=lambda all=False: partitions,
        disk_usage=lambda mountpoint: usages[mountpoint],
    )
    sf_rpi_status = types.SimpleNamespace(
        get_disks=lambda: ['/dev/nvme0n1'],
        get_disk_type=lambda disk: 'nvme',
        DiskInfo=DiskInfo,
    )
    monkeypatch.setitem(sys.modules, 'psutil', psutil)
    monkeypatch.setitem(sys.modules, 'sf_rpi_status', sf_rpi_status)

    info = launcher.get_disks_info()
    disk = info['/dev/nvme0n1']
    assert (disk.total, disk.used, disk.free) == (1100, 510, 590)
    assert disk.percent == round(510 / 1100 * 100, 2)
    assert disk.mounted and disk.type == 'nvme'
