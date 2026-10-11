#!/usr/bin/env python3
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Change Pironman 5 settings on Recalbox; used by the Recalbox menu scripts.

  pironman5ctl.py set rgb_color '"#ff0000"'   value as JSON (or plain text)
  pironman5ctl.py cycle rgb_style             next value
  pironman5ctl.py toggle rgb_enable           true <-> false
  pironman5ctl.py get [key]
  pironman5ctl.py status                      print settings, show them on the OLED
  pironman5ctl.py install-scripts             add the entries to the Recalbox menu
  pironman5ctl.py remove-scripts [dest]       remove them (moved to dest if given)

The running service applies config.json changes within a second.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm5r import CONFIG_PATH, TOAST_REQUEST_PATH, menu, settings  # noqa: E402

STATUS_KEYS = ('rgb_enable', 'rgb_style', 'rgb_color', 'rgb_brightness',
               'rgb_system_colors', 'gpio_fan_mode', 'oled_enable')


def load():
    try:
        config = settings.load_config(CONFIG_PATH)
    except FileNotFoundError:
        config = {}
    config.setdefault('system', {})
    return config


def parse_value(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def change(key, value):
    config = load()
    config['system'][key] = value
    settings.save_config(CONFIG_PATH, config)
    lang = settings.language()
    menu.refresh(config['system'], lang, menu.MANUAL_SCRIPTS)
    title, shown = settings.label(lang, key, value)
    print(f'{title}: {shown}')


def request_status_toast():
    tmp = f'{TOAST_REQUEST_PATH}.tmp'
    with open(tmp, 'w') as f:
        json.dump({'type': 'status'}, f)
    os.replace(tmp, TOAST_REQUEST_PATH)


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    command, args = argv[0], argv[1:]
    system = load()['system']
    if command == 'set' and len(args) == 2:
        change(args[0], parse_value(args[1]))
    elif command == 'cycle' and len(args) == 1 and args[0] in settings.CYCLES:
        change(args[0], settings.next_value(args[0], system.get(args[0])))
    elif command == 'toggle' and len(args) == 1 and args[0] in settings.TOGGLES:
        change(args[0], not settings.get(system, args[0]))
    elif command == 'get':
        for key in args or sorted(system):
            print(f'{key} = {json.dumps(settings.get(system, key))}')
    elif command == 'status':
        for key in STATUS_KEYS:
            print(f'{key} = {json.dumps(settings.get(system, key))}')
        request_status_toast()
    elif command == 'install-scripts':
        menu.remove(menu.MANUAL_SCRIPTS)  # names depend on language and settings
        count = menu.refresh(system, settings.language(), menu.MANUAL_SCRIPTS, create=True)
        print(f'{count} entries added to {menu.MANUAL_SCRIPTS}')
    elif command == 'remove-scripts':
        print(f'{menu.remove(menu.MANUAL_SCRIPTS, args[0] if args else None)} entries removed')
    else:
        print(f'Invalid command: {" ".join(argv)}\n', file=sys.stderr)
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
