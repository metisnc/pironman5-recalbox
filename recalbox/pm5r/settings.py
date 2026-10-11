# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Settings changed from the Recalbox menu, their labels and translations."""
import json
import os

RECALBOX_CONF = '/recalbox/share/system/recalbox.conf'

# Defaults of the Recalbox-only keys (not known by the upstream service)
DEFAULTS = {
    'oled_page_interval': 10,
    'oled_game_page': True,
    'rgb_system_colors': True,
}

RGB_STYLES = ['solid', 'breathing', 'flow', 'rainbow', 'hue_cycle']
RGB_COLORS = ['#ffffff', '#ff0000', '#ff6000', '#ffd000', '#00ff00',
              '#00d0ff', '#0040ff', '#a000ff', '#ff00a0']
RGB_BRIGHTNESS = [25, 50, 75, 100]
FAN_MODES = [0, 1, 2, 3, 4]

# setting key -> values cycled by the menu scripts (booleans are toggled)
CYCLES = {
    'rgb_style': RGB_STYLES,
    'rgb_color': RGB_COLORS,
    'rgb_brightness': RGB_BRIGHTNESS,
    'gpio_fan_mode': FAN_MODES,
}
TOGGLES = ['rgb_enable', 'rgb_system_colors', 'oled_enable', 'oled_game_page']

TEXTS = {
    'fr': {
        'rgb_style': 'LEDs', 'rgb_color': 'Couleur LEDs',
        'rgb_brightness': 'Luminosité', 'rgb_enable': 'LEDs',
        'rgb_system_colors': 'Couleur système', 'gpio_fan_mode': 'Ventilateurs',
        'oled_enable': 'Écran', 'oled_game_page': 'Page En jeu',
        'on': 'allumées', 'off': 'éteintes', 'yes': 'oui', 'no': 'non',
        'screen_on': 'allumé', 'screen_off': 'éteint',
        'solid': 'fixe', 'breathing': 'respiration', 'flow': 'défilement',
        'flow_reverse': 'défilement inv.', 'rainbow': 'arc-en-ciel',
        'rainbow_reverse': 'arc-en-ciel inv.', 'hue_cycle': 'cycle couleurs',
        'fan_0': 'toujours', 'fan_1': 'performance', 'fan_2': 'frais',
        'fan_3': 'équilibré', 'fan_4': 'silencieux',
        '#ffffff': 'blanc', '#ff0000': 'rouge', '#ff6000': 'orange',
        '#ffd000': 'jaune', '#00ff00': 'vert', '#00d0ff': 'cyan',
        '#0040ff': 'bleu', '#a000ff': 'violet', '#ff00a0': 'rose',
        'status': 'État', 'fan': 'ventilo',
    },
    'en': {
        'rgb_style': 'LEDs', 'rgb_color': 'LED color',
        'rgb_brightness': 'Brightness', 'rgb_enable': 'LEDs',
        'rgb_system_colors': 'System color', 'gpio_fan_mode': 'Case fans',
        'oled_enable': 'Screen', 'oled_game_page': 'Now playing page',
        'on': 'on', 'off': 'off', 'yes': 'yes', 'no': 'no',
        'screen_on': 'on', 'screen_off': 'off',
        'solid': 'solid', 'breathing': 'breathing', 'flow': 'flow',
        'flow_reverse': 'flow reverse', 'rainbow': 'rainbow',
        'rainbow_reverse': 'rainbow reverse', 'hue_cycle': 'hue cycle',
        'fan_0': 'always on', 'fan_1': 'performance', 'fan_2': 'cool',
        'fan_3': 'balanced', 'fan_4': 'quiet',
        '#ffffff': 'white', '#ff0000': 'red', '#ff6000': 'orange',
        '#ffd000': 'yellow', '#00ff00': 'green', '#00d0ff': 'cyan',
        '#0040ff': 'blue', '#a000ff': 'purple', '#ff00a0': 'pink',
        'status': 'Status', 'fan': 'fan',
    },
}

def language(conf_path=RECALBOX_CONF):
    """'fr' or 'en' from system.language in recalbox.conf."""
    try:
        with open(conf_path, encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('system.language='):
                    return 'fr' if line.split('=', 1)[1].strip().startswith('fr') else 'en'
    except OSError:
        pass
    return 'en'


def text(lang, key):
    return TEXTS.get(lang, TEXTS['en']).get(key, key)


def label(lang, key, value):
    """(title, value) shown on the OLED for a changed setting."""
    t = TEXTS.get(lang, TEXTS['en'])
    if key == 'rgb_enable':
        shown = t['on'] if value else t['off']
    elif key == 'oled_enable':
        shown = t['screen_on'] if value else t['screen_off']
    elif isinstance(value, bool):
        shown = t['yes'] if value else t['no']
    elif key == 'gpio_fan_mode':
        shown = t.get(f'fan_{value}', str(value))
    elif key == 'rgb_brightness':
        shown = f'{value} %'
    elif isinstance(value, str):
        shown = t.get(value.lower(), value)
    else:
        shown = str(value)
    return t.get(key, key), shown


def next_value(key, current):
    """Value after `current` in the cycle of `key`."""
    values = CYCLES[key]
    if isinstance(current, str):
        current = current.lower()
    try:
        return values[(values.index(current) + 1) % len(values)]
    except ValueError:
        return values[0]


def load_config(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_config(path, config):
    """Atomic write, so the service never reads a half-written file."""
    tmp = f'{path}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def get(system, key):
    return system.get(key, DEFAULTS.get(key))
