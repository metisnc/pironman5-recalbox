# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Entries of the Recalbox "User scripts" menu.

EmulationStation shows the script file name in the menu and in its "script
started" message, and cannot display custom text. Each entry is therefore
named after the current value and the result it produces
("LEDs · brightness (75 %) → 100 %") and applies that explicit value;
entries are renamed after every change.
"""
import json
import os
import shutil

from . import settings

MANUAL_SCRIPTS = '/recalbox/share/userscripts/manual'
MARKER = '# pironman5-recalbox menu entry'
PREFIX = 'Pironman · '
CTL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'pironman5ctl.py')

# A fixed part, then " → " and the result. The fixed parts differ before the
# arrow (even ignoring punctuation and accents), so the alphabetical order of
# the menu never changes when the results do.
NAMES = {
    'fr': {
        'rgb_enable': ('LEDs · allumage', 'allumer', 'éteindre'),
        'rgb_color': 'LEDs · couleur',
        'rgb_brightness': 'LEDs · luminosité',
        'rgb_system_colors': ('LEDs · selon le système', 'activer', 'désactiver'),
        'rgb_style': 'LEDs · style',
        'gpio_fan_mode': 'Ventilateurs · mode',
        'gpio_fan_led': 'Ventilateurs · LEDs',
        'sleep_sync': ('Veille · synchronisation', 'activer', 'désactiver'),
        'oled_enable': ('Écran · allumage', 'allumer', 'éteindre'),
    },
    'en': {
        'rgb_enable': ('LEDs · power', 'turn on', 'turn off'),
        'rgb_color': 'LEDs · color',
        'rgb_brightness': 'LEDs · brightness',
        'rgb_system_colors': ('LEDs · per system', 'enable', 'disable'),
        'rgb_style': 'LEDs · style',
        'gpio_fan_mode': 'Case fans · mode',
        'gpio_fan_led': 'Case fans · LEDs',
        'sleep_sync': ('Screensaver · sync', 'enable', 'disable'),
        'oled_enable': ('Screen · power', 'turn on', 'turn off'),
    },
}
ARROW = ' → '
CYCLED = ['rgb_style', 'rgb_color', 'rgb_brightness', 'gpio_fan_mode', 'gpio_fan_led']
TOGGLED = ['rgb_enable', 'rgb_system_colors', 'oled_enable', 'sleep_sync']


def entries(system, lang, variant='base'):
    """{menu name: pironman5ctl arguments} for the current settings."""
    names = NAMES.get(lang, NAMES['en'])
    result = {}
    for key in CYCLED:
        if key == 'gpio_fan_led' and variant not in settings.FAN_LED_VARIANTS:
            continue
        current = settings.get(system, key)
        value = settings.next_value(key, current)
        now = settings.label(lang, key, current)[1] if current is not None else '?'
        shown = settings.label(lang, key, value)[1]
        # "Case fans · mode (cool) → balanced": current value, then the result
        result[f'{names[key]} ({now}){ARROW}{shown}'] = ['set', key, json.dumps(value)]
    for key in TOGGLED:
        fixed, turn_on, turn_off = names[key]
        current = bool(settings.get(system, key))
        result[fixed + ARROW + (turn_off if current else turn_on)] = \
            ['set', key, json.dumps(not current)]
    return result


def script_body(args):
    quoted = ' '.join("'" + a.replace("'", "'\\''") + "'" for a in args)
    return f'#!/bin/sh\n{MARKER}\nexec python3 "{CTL}" {quoted}\n'


def is_ours(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return MARKER in f.read(512)
    except OSError:
        return False


def installed(directory=MANUAL_SCRIPTS):
    if not os.path.isdir(directory):
        return []
    return [name for name in os.listdir(directory)
            if is_ours(os.path.join(directory, name))]


def refresh(system, lang, directory=MANUAL_SCRIPTS, create=False, variant=None):
    """Rename the entries to match the settings.

    Only touches files carrying MARKER. Does nothing unless entries are
    already installed or create is True (so it never re-adds removed entries).
    """
    current = installed(directory)
    if not current and not create:
        return 0
    os.makedirs(directory, exist_ok=True)
    variant = variant or settings.variant()
    wanted = {f'{PREFIX}{name}.sh': script_body(args)
              for name, args in entries(system, lang, variant).items()}
    for name in current:
        if name not in wanted:
            os.remove(os.path.join(directory, name))
    for name, body in wanted.items():
        path = os.path.join(directory, name)
        if name not in current:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(body)
    return len(wanted)


def remove(directory=MANUAL_SCRIPTS, dest=None):
    names = installed(directory)
    for name in names:
        path = os.path.join(directory, name)
        if dest:
            os.makedirs(dest, exist_ok=True)
            shutil.move(path, os.path.join(dest, name))
        else:
            os.remove(path)
    return len(names)
