# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Recalbox integration for the pironman5 service.

settings  settings that can be changed from the Recalbox menu, i18n
control   config.json watcher and OLED message requests
es_events EmulationStation game start/stop detection
oled      OLED message overlay and "now playing" page
colors    RGB LED color per console manufacturer
"""
import os

PM5_HOME = os.environ.get('PM5_HOME', '/recalbox/share/pironman5')
CONFIG_PATH = os.path.join(PM5_HOME, 'config.json')
TOAST_REQUEST_PATH = '/tmp/pironman5-toast.json'
