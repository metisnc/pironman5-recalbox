# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""RGB LED color of the console manufacturer of the running game."""
import xml.etree.ElementTree as ET

SYSTEMLISTS = [
    '/recalbox/share/system/.emulationstation/systemlist.xml',  # user override
    '/recalbox/share_init/system/.emulationstation/systemlist.xml',
]

MANUFACTURER_COLORS = {
    'nintendo': '#ff0000',
    'sega': '#0040ff',
    'sony': '#a000ff',
    'microsoft': '#00ff00',
    'snk': '#00d0ff',
    'nec': '#ff6000',
    'atari': '#ffd000',
    'bandai': '#ff00a0',
}
ARCADE_COLOR = '#ff00ff'
ARCADE_MANUFACTURERS = {'mame', 'fbn', 'namco', 'capcom', 'seta', 'sammy',
                        'nichibutsu', 'daphne'}
ARCADE_TYPES = {'arcade'}


def load_systems(paths=SYSTEMLISTS):
    """{system name: (manufacturer, type)} from the first readable systemlist."""
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        systems = {}
        for system in root.iter('system'):
            props = system.find('properties')
            if props is None:
                continue
            systems[system.get('name')] = (props.get('manufacturer', ''),
                                           props.get('type', ''))
        return systems
    return {}


def color_for(system_id, systems):
    """LED color for a system, or None to keep the user color."""
    manufacturer, kind = systems.get(system_id, ('', ''))
    manufacturer = manufacturer.lower()
    if manufacturer in MANUFACTURER_COLORS:
        return MANUFACTURER_COLORS[manufacturer]
    if kind in ARCADE_TYPES or manufacturer in ARCADE_MANUFACTURERS:
        return ARCADE_COLOR
    return None
