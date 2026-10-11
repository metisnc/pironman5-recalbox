# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Tests for the Recalbox integration (pm5r) and pironman5ctl."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pm5r import colors, settings  # noqa: E402
from pm5r.es_events import GameWatcher, parse_state  # noqa: E402


# ------------------------------------------------------------ settings
def test_next_value_cycles_and_recovers_from_unknown_values():
    assert settings.next_value('rgb_style', 'solid') == 'breathing'
    assert settings.next_value('rgb_style', 'hue_cycle') == 'solid'
    assert settings.next_value('rgb_style', 'flow_reverse') == 'solid'
    assert settings.next_value('rgb_color', '#FF0000') == '#ff6000'
    assert settings.next_value('gpio_fan_mode', 4) == 0


def test_labels_are_translated():
    assert settings.label('fr', 'rgb_style', 'rainbow') == ('LEDs', 'arc-en-ciel')
    assert settings.label('en', 'gpio_fan_mode', 1) == ('Case fans', 'performance')
    assert settings.label('fr', 'rgb_enable', False) == ('LEDs', 'éteintes')
    assert settings.label('fr', 'rgb_brightness', 75) == ('Luminosité', '75 %')
    assert settings.label('fr', 'rgb_color', '#0040ff') == ('Couleur LEDs', 'bleu')


def test_language_from_recalbox_conf(tmp_path):
    conf = tmp_path / 'recalbox.conf'
    conf.write_text('system.language=fr_FR\n')
    assert settings.language(str(conf)) == 'fr'
    conf.write_text('system.language=de_DE\n')
    assert settings.language(str(conf)) == 'en'
    assert settings.language(str(tmp_path / 'missing')) == 'en'


def test_menu_entries_name_the_result():
    from pm5r import menu
    system = {'rgb_style': 'breathing', 'rgb_brightness': 75, 'rgb_enable': True,
              'gpio_fan_mode': 1, 'oled_enable': True, 'rgb_color': '#ffffff'}
    entries = menu.entries(system, 'fr')
    assert entries['LEDs · luminosité (75 %) → 100 %'] == ['set', 'rgb_brightness', '100']
    assert entries['LEDs · style (respiration) → défilement'] == ['set', 'rgb_style', '"flow"']
    assert entries['LEDs · couleur (blanc) → rouge'] == ['set', 'rgb_color', '"#ff0000"']
    assert entries['LEDs · allumage → éteindre'] == ['set', 'rgb_enable', 'false']
    assert entries['LEDs · selon le système → désactiver'][2] == 'false'
    assert entries['Ventilateurs · mode (performance) → frais'] == ['set', 'gpio_fan_mode', '2']
    assert entries['Écran · allumage → éteindre'] == ['set', 'oled_enable', 'false']
    assert len(entries) == 7
    for lang in ('fr', 'en'):
        for name in menu.entries(system, lang):
            assert not set(name) & set('"*/:<>?\\|')  # valid exFAT file names


def _all_states():
    from pm5r import menu
    states = [{}]
    for key in menu.CYCLED:
        for value in settings.CYCLES[key]:
            states.append({key: value})
    for key in menu.TOGGLED:
        for value in (True, False):
            states.append({key: value})
    return states


def _loose(name):
    """Collation ignoring case, accents, spaces and punctuation."""
    import unicodedata
    plain = unicodedata.normalize('NFKD', name.casefold())
    return ''.join(c for c in plain if c.isalnum())


def test_menu_order_never_changes():
    from pm5r import menu
    for lang in ('fr', 'en'):
        for collate in (str, _loose):
            orders = set()
            for state in _all_states():
                names = sorted(menu.entries(state, lang), key=collate)
                orders.add(tuple(name.split(' (')[0].split(menu.ARROW)[0] for name in names))
            assert len(orders) == 1, (lang, collate, orders)


def test_save_config_is_atomic(tmp_path):
    path = tmp_path / 'config.json'
    settings.save_config(str(path), {'system': {'rgb_style': 'solid'}})
    assert json.loads(path.read_text()) == {'system': {'rgb_style': 'solid'}}
    assert not (tmp_path / 'config.json.tmp').exists()


# ------------------------------------------------------------ colors
def test_colors_by_manufacturer(tmp_path):
    xml = tmp_path / 'systemlist.xml'
    xml.write_text(
        '<systemList>'
        '<system name="snes"><properties manufacturer="Nintendo" type="console"/></system>'
        '<system name="model2"><properties manufacturer="Sega" type="arcade"/></system>'
        '<system name="mame"><properties manufacturer="Mame" type="arcade"/></system>'
        '<system name="doom"><properties manufacturer="port" type="port"/></system>'
        '</systemList>')
    systems = colors.load_systems([str(tmp_path / 'missing.xml'), str(xml)])
    assert colors.color_for('snes', systems) == '#ff0000'
    assert colors.color_for('model2', systems) == '#0040ff'
    assert colors.color_for('mame', systems) == colors.ARCADE_COLOR
    assert colors.color_for('doom', systems) is None
    assert colors.color_for('unknown', systems) is None


# ------------------------------------------------------------ ES events
STATE = """Version=2.0
Action=rungame
System=Sega Model 2
SystemId=model2
Game=Zero Gunner
GamePath=/recalbox/share/roms/model2/zerogun.zip
Publisher=Psikyo
"""


def test_parse_state():
    state = parse_state(STATE)
    assert state['Action'] == 'rungame' and state['Game'] == 'Zero Gunner'


def test_game_watcher_start_and_end(tmp_path):
    path = tmp_path / 'es_state.inf'
    events = []
    log = types.SimpleNamespace(info=lambda *a: None, exception=lambda *a: None)
    watcher = GameWatcher(lambda game: events.append(('start', game.title)),
                          lambda: events.append(('end',)), log, path=str(path))
    watcher.poll()  # no file yet
    path.write_text(STATE)
    watcher.poll()
    assert watcher.game.system_id == 'model2'
    os.utime(path, (1, 1))
    path.write_text(STATE.replace('rungame', 'endgame'))
    watcher.poll()
    path.write_text(STATE.replace('rungame', 'gamelistbrowsing'))
    os.utime(path, (2, 2))
    watcher.poll()
    assert events == [('start', 'Zero Gunner'), ('end',)]
    assert watcher.game is None


# ------------------------------------------------------------ pironman5ctl
@pytest.fixture
def ctl(tmp_path, monkeypatch):
    import pm5r
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'system': {'rgb_style': 'solid', 'rgb_enable': True}}))
    import pironman5ctl
    monkeypatch.setattr(pironman5ctl, 'CONFIG_PATH', str(config))
    monkeypatch.setattr(pironman5ctl, 'TOAST_REQUEST_PATH', str(tmp_path / 'toast.json'))
    from pm5r import menu
    monkeypatch.setattr(menu, 'MANUAL_SCRIPTS', str(tmp_path / 'manual'))
    monkeypatch.setattr(settings, 'language', lambda *args: 'fr')
    monkeypatch.setattr(pm5r, 'CONFIG_PATH', str(config))
    return pironman5ctl, config, tmp_path


def test_ctl_cycle_toggle_set(ctl):
    pironman5ctl, config, _ = ctl
    assert pironman5ctl.main(['cycle', 'rgb_style']) == 0
    assert pironman5ctl.main(['toggle', 'rgb_enable']) == 0
    assert pironman5ctl.main(['toggle', 'rgb_system_colors']) == 0  # default true
    assert pironman5ctl.main(['set', 'rgb_brightness', '50']) == 0
    system = json.loads(config.read_text())['system']
    assert system == {'rgb_style': 'breathing', 'rgb_enable': False,
                      'rgb_system_colors': False, 'rgb_brightness': 50}
    assert pironman5ctl.main(['cycle', 'not_a_setting']) == 2


def test_ctl_menu_entries_install_rename_remove(ctl):
    pironman5ctl, _, tmp_path = ctl
    manual = tmp_path / 'manual'
    manual.mkdir()
    (manual / 'someone else.sh').write_text('#!/bin/sh\necho hi\n')
    assert pironman5ctl.main(['install-scripts']) == 0
    ours = sorted(n for n in os.listdir(manual) if n.startswith('Pironman · '))
    assert len(ours) == 7
    assert 'Pironman · LEDs · style (fixe) → respiration.sh' in ours
    body = (manual / 'Pironman · LEDs · style (fixe) → respiration.sh').read_text()
    assert "'set' 'rgb_style' '\"breathing\"'" in body
    # running an entry renames the entries after the new settings
    assert pironman5ctl.main(['set', 'rgb_style', '"breathing"']) == 0
    names = os.listdir(manual)
    assert 'Pironman · LEDs · style (respiration) → défilement.sh' in names
    assert 'Pironman · LEDs · style (fixe) → respiration.sh' not in names
    assert len([n for n in names if n.startswith('Pironman')]) == 7
    assert pironman5ctl.main(['remove-scripts', str(tmp_path / 'backup')]) == 0
    assert os.listdir(manual) == ['someone else.sh']
    assert len(os.listdir(tmp_path / 'backup')) == 7


def test_ctl_set_does_not_create_menu_entries_when_not_installed(ctl):
    pironman5ctl, _, tmp_path = ctl
    assert pironman5ctl.main(['set', 'rgb_brightness', '50']) == 0
    assert not (tmp_path / 'manual').exists()


def test_ctl_status_requests_toast(ctl):
    pironman5ctl, _, tmp_path = ctl
    assert pironman5ctl.main(['status']) == 0
    assert json.loads((tmp_path / 'toast.json').read_text()) == {'type': 'status'}


# ------------------------------------------------------------ OLED and control (need pm_auto)
def test_oled_text_helpers():
    pytest.importorskip('PIL')
    pytest.importorskip('pm_auto')
    from pm5r import oled
    assert oled.format_elapsed(75) == '1:15'
    assert oled.format_elapsed(3725) == '1:02:05'
    lines = oled.wrap('Daytona USA 2 Power Edition Battle On The Edge Deluxe', 14)
    assert len(lines) == 2 and lines[1].endswith('…')
    assert all(oled.text_width(line, 14) <= oled.WIDTH for line in lines)


class FakeAddon:
    def __init__(self):
        self.calls = []
        self.oled_pages = ['mix']
        self.last_page_index = 0
        self.wake_flag = True

    def update_config(self, config):
        self.calls.append(dict(config))

    def update_pages(self, pages):
        self.calls.append(('pages', list(pages)))


def make_integration(tmp_path, monkeypatch):
    pytest.importorskip('PIL')
    pytest.importorskip('pm_auto')
    from pm5r import control
    monkeypatch.setattr(control.colors, 'load_systems',
                        lambda: {'snes': ('Nintendo', 'console')})
    monkeypatch.setattr(control, 'TOAST_REQUEST_PATH', str(tmp_path / 'toast.json'))
    config = tmp_path / 'config.json'
    system = {'rgb_style': 'rainbow', 'rgb_color': '#ffffff', 'oled_enable': True}
    config.write_text(json.dumps({'system': system}))
    leds, screen = FakeAddon(), FakeAddon()
    updates = []
    app = types.SimpleNamespace(
        config={'system': dict(system)},
        update_config=lambda c: updates.append(c['system']),
        pm_auto=types.SimpleNamespace(addons=types.SimpleNamespace(
            addons={'ws2812': leds, 'oled': screen}), loop=None, read=lambda: {}))
    log = types.SimpleNamespace(info=lambda *a: None, warning=lambda *a: None,
                                exception=lambda *a: None)
    integration = control.Integration(app, log, config_path=str(config),
                                      menu_dir=str(tmp_path / 'manual'))
    return integration, app, config, updates, leds, screen


def test_integration_applies_only_changed_keys(tmp_path, monkeypatch):
    integration, app, config, updates, _, screen = make_integration(tmp_path, monkeypatch)
    data = json.loads(config.read_text())
    data['system']['rgb_style'] = 'solid'
    data['system']['rgb_system_colors'] = False
    config.write_text(json.dumps(data))
    os.utime(config, (10, 10))
    integration.poll()
    assert updates == [{'rgb_style': 'solid', 'rgb_system_colors': False}]
    assert app.config['system']['rgb_system_colors'] is False
    updates.clear()
    integration.poll()  # unchanged file: nothing applied again
    assert updates == []


def test_integration_pin_settings_wait_for_restart(tmp_path, monkeypatch):
    integration, app, config, updates, _, _ = make_integration(tmp_path, monkeypatch)
    data = json.loads(config.read_text())
    data['system'].update({'gpio_fan_led': 'off', 'gpio_fan_led_pin': 5,
                           'gpio_fan_mode': 4})
    config.write_text(json.dumps(data))
    os.utime(config, (30, 30))
    integration.poll()
    assert updates == [{'gpio_fan_mode': 4}]  # pins not changed live
    assert app.config['system']['gpio_fan_led_pin'] == 5  # but kept and saved


def test_integration_single_change_shows_toast(tmp_path, monkeypatch):
    integration, _, config, _, _, screen = make_integration(tmp_path, monkeypatch)
    integration.lang = 'fr'
    data = json.loads(config.read_text())
    data['system']['rgb_style'] = 'flow'
    config.write_text(json.dumps(data))
    os.utime(config, (20, 20))
    integration.poll()
    assert integration.toast.active()
    assert integration.toast.lines == ['LEDs', 'défilement']
    assert screen.last_page_index == -1


def test_integration_game_color_and_page(tmp_path, monkeypatch):
    from pm5r.es_events import Game
    integration, _, _, _, leds, screen = make_integration(tmp_path, monkeypatch)
    integration.games.game = Game({'SystemId': 'snes', 'System': 'Super Nintendo',
                                   'Game': 'Zelda'})
    integration._game_started()
    # rainbow ignores the color: breathing in the Nintendo color during the game
    assert {'rgb_color': '#ff0000', 'rgb_style': 'breathing'} in leds.calls
    assert ('pages', ['game']) in screen.calls  # game page only, no rotation
    integration.games.game = None
    integration._game_ended()
    assert leds.calls[-1] == {'rgb_color': '#ffffff', 'rgb_style': 'rainbow'}
    assert screen.calls[-1] == ('pages', ['mix'])
