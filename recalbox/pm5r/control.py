# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Recalbox integration of a running Pironman5 service.

- applies config.json changes live (menu scripts, pironman5ctl, SMB edits)
- shows a confirmation on the OLED for each change
- EmulationStation games: "now playing" OLED page, LED color per manufacturer

Every change to the addons runs in pm_auto's asyncio loop thread, so it never
races with the OLED / LED / fan loops.
"""
import json
import os
import threading

from . import CONFIG_PATH, TOAST_REQUEST_PATH, colors, menu, oled, settings
from .es_events import GameWatcher

# Styles that ignore rgb_color: use breathing while showing a system color
COLORLESS_STYLES = {'rainbow', 'rainbow_reverse', 'hue_cycle'}
# Keys applied after the OLED confirmation, since they switch the screen off
DELAYED_OFF = {'oled_enable'}
# Pin settings: pm_auto fails to change them while running; they are saved
# and used at the next service start. gpio_fan_led too on a case without
# fan LEDs (Pironman 5): pm_auto would fail on the missing LED.
RESTART_ONLY = {'gpio_fan_pin', 'gpio_fan_led_pin'}
TOAST_SECONDS = 3
# Case fan LED modes understood by pm_auto; 'rgb' (like the RGB LEDs) is ours
FAN_LED_NATIVE = ('follow', 'on', 'off')
FAN_LED_KEYS = {'gpio_fan_led', 'rgb_enable', 'sleep_sync'}


def patch_fan_addon():
    """Let pm_auto's FanAddon accept gpio_fan_led = 'rgb' at start-up.

    Must run before the service creates its addons. The real value is then
    applied by Integration once the service runs.
    """
    import pm_auto.addons.fan as fan
    original = fan.FanAddon.update_config

    def update_config(self, config, init=False):
        if isinstance(config, dict) and config.get('gpio_fan_led') not in (None,) + FAN_LED_NATIVE:
            config = dict(config, gpio_fan_led='on' if config.get('rgb_enable', True) else 'off')
        return original(self, config, init=init)

    fan.FanAddon.update_config = update_config


class Integration:

    def __init__(self, app, log, config_path=CONFIG_PATH, poll_interval=1.0,
                 menu_dir=menu.MANUAL_SCRIPTS):
        self.app = app
        self.log = log
        self.config_path = config_path
        self.menu_dir = menu_dir
        self.poll_interval = poll_interval
        self.lang = settings.language()
        self.toast = oled.Toast()
        self.systems = colors.load_systems()
        self.games = GameWatcher(self._on_game_start, self._on_game_end, log,
                                 on_sleep=self._on_sleep, on_wake=self._on_wake)
        self.restart_only = set(RESTART_ONLY)
        if 'gpio_fan_led' not in getattr(app, 'peripherals', []):
            self.restart_only.add('gpio_fan_led')
        self._mtime = self._stat()
        self._fan_led_applied = False
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run, name='recalbox-control', daemon=True)

    # ------------------------------------------------------------ lifecycle
    def start(self):
        self._thread.start()
        self.games.start()

    def stop(self):
        self._stopping.set()
        self._thread.join()
        self.games.stop()

    @property
    def system(self):
        return self.app.config['system']

    def addon(self, name):
        return self.app.pm_auto.addons.addons.get(name)

    def in_loop(self, func, *args):
        loop = getattr(self.app.pm_auto, 'loop', None)
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._safe, func, *args)
        else:
            self._safe(func, *args)

    def _safe(self, func, *args):
        try:
            func(*args)
        except Exception:
            self.log.exception('Recalbox integration error')

    # ------------------------------------------------------------ OLED
    def show(self, lines, duration=TOAST_SECONDS):
        def show_now():
            self.toast.show(lines, duration)
            screen = self.addon('oled')
            if screen is not None:
                screen.last_page_index = -1  # redraw now
        self.in_loop(show_now)

    def refresh_pages(self):
        """OLED pages: only the game page during a game, else the configured ones."""
        screen = self.addon('oled')
        if screen is None:
            return
        if self.games.game is not None and settings.get(self.system, 'oled_game_page'):
            names = [oled.GAME_PAGE]  # a single page: the rotation has no effect
        else:
            names = list(screen.oled_pages)
        screen.update_pages(pages=names)

    def status_lines(self):
        t = lambda key: settings.text(self.lang, key)  # noqa: E731
        s = self.system
        data = self.app.pm_auto.read() or {}
        style = settings.label(self.lang, 'rgb_style', s.get('rgb_style'))[1]
        if not s.get('rgb_enable', True):
            style = t('off')
        color = settings.label(self.lang, 'rgb_color', s.get('rgb_color', ''))[1]
        fans = settings.label(self.lang, 'gpio_fan_mode', s.get('gpio_fan_mode'))[1]
        system_color = t('yes') if settings.get(s, 'rgb_system_colors') else t('no')
        return [
            f"{t('rgb_style')}: {style}, {color}",
            f"{t('rgb_brightness')}: {s.get('rgb_brightness')} %",
            f"{t('rgb_system_colors')}: {system_color}",
            f"{t('gpio_fan_mode')}: {fans}",
            f"CPU {int(data.get('cpu_temperature', 0) or 0)}°C  {t('fan')} "
            f"{data.get('pwm_fan_speed', 0)} rpm",
        ]

    # ------------------------------------------------------------ config
    def _stat(self):
        try:
            return os.stat(self.config_path).st_mtime
        except OSError:
            return None

    def poll(self):
        if os.path.exists(TOAST_REQUEST_PATH):
            self._handle_toast_request()
        mtime = self._stat()
        if mtime is None or mtime == self._mtime:
            return
        self._mtime = mtime
        try:
            new = settings.load_config(self.config_path).get('system', {})
        except (OSError, ValueError) as e:
            self.log.warning('Ignoring unreadable config.json: %s', e)
            return
        changes = {k: v for k, v in new.items() if self.system.get(k) != v}
        if changes:
            self.in_loop(self.apply, changes)

    def _handle_toast_request(self):
        try:
            with open(TOAST_REQUEST_PATH, encoding='utf-8') as f:
                request = json.load(f)
        except (OSError, ValueError):
            request = {}
        try:
            os.remove(TOAST_REQUEST_PATH)
        except OSError:
            pass
        if request.get('type') == 'status':
            self.show(self.status_lines(), duration=6)

    def apply(self, changes):
        """Apply changed settings live (runs in the asyncio loop thread)."""
        self.log.info('config.json changed: %s', changes)
        restart_only = sorted(k for k in changes if k in self.restart_only)
        if restart_only:
            self.log.info('Applied at next service start: %s', ', '.join(restart_only))
        # gpio_fan_led goes through _apply_fan_led(), never to pm_auto as is
        live = {k: v for k, v in changes.items()
                if k not in self.restart_only and k != 'gpio_fan_led'}
        now = {k: v for k, v in live.items()
               if not (k in DELAYED_OFF and v is False)}
        later = {k: v for k, v in live.items() if k not in now}
        # In-memory config first: update_config() rewrites config.json, which
        # the watcher re-reads; it must then see no difference.
        self.system.update(changes)
        if now:
            self.app.update_config({'system': now})
        if len(changes) == 1:
            key, value = next(iter(changes.items()))
            self.toast.show(settings.label(self.lang, key, value), TOAST_SECONDS)
            screen = self.addon('oled')
            if screen is not None:
                screen.last_page_index = -1
        if self.games.game is not None:
            self._apply_game_color()
            if 'oled_pages' in changes or 'oled_game_page' in changes:
                self.refresh_pages()
        if later:
            # Let the confirmation show before the screen goes off
            loop = self.app.pm_auto.loop
            loop.call_later(TOAST_SECONDS, self._safe, self._apply_later, later)
        if FAN_LED_KEYS & set(changes):
            self._apply_fan_led()
        if self.games.sleeping:
            self._apply_sleep()  # a change must not light up a sleeping case
        # Menu entry names show the result of the next action
        menu.refresh(self.system, self.lang, self.menu_dir)

    def _apply_later(self, changes):
        self.app.update_config({'system': changes})

    def _run(self):
        while not self._stopping.wait(self.poll_interval):
            try:
                if not self._fan_led_applied and self._loop_running():
                    # pm_auto starts the fan LEDs in 'follow' whatever the
                    # saved setting: apply it once the service runs
                    self._fan_led_applied = True
                    self.in_loop(self._apply_fan_led)
                self.poll()
            except Exception:
                self.log.exception('config watcher error')

    def _loop_running(self):
        loop = getattr(self.app.pm_auto, 'loop', None)
        return loop is not None and loop.is_running()

    # ------------------------------------------------------------ fan LEDs
    def fan_led_value(self):
        """pm_auto value of the case fan LEDs for the gpio_fan_led setting."""
        mode = settings.get(self.system, 'gpio_fan_led')
        if mode == 'rgb':
            asleep = self.games.sleeping and settings.get(self.system, 'sleep_sync')
            lit = self.system.get('rgb_enable', True) and not asleep
            return 'on' if lit else 'off'
        return mode if mode in FAN_LED_NATIVE else 'follow'

    def _apply_fan_led(self):
        fan = self.addon('fan')
        if fan is None or 'gpio_fan_led' not in getattr(self.app, 'peripherals', []):
            return
        fan.update_config({'gpio_fan_led': self.fan_led_value()})

    # ------------------------------------------------------------ screensaver
    def _on_sleep(self):
        self.in_loop(self._apply_sleep)

    def _on_wake(self):
        self.in_loop(self._apply_wake)

    def _apply_sleep(self):
        """EmulationStation screensaver: OLED and RGB LEDs off (not saved)."""
        if not settings.get(self.system, 'sleep_sync'):
            return
        screen, leds = self.addon('oled'), self.addon('ws2812')
        if screen is not None:
            screen.sleep()
        if leds is not None:
            leds.update_config({'rgb_enable': False})
        self._apply_fan_led()

    def _apply_wake(self):
        screen, leds = self.addon('oled'), self.addon('ws2812')
        if screen is not None and self.system.get('oled_enable', True):
            screen.wake()
            screen.last_page_index = -1
        if leds is not None:
            leds.update_config({'rgb_enable': self.system.get('rgb_enable', True)})
        self._apply_fan_led()

    # ------------------------------------------------------------ games
    def _on_game_start(self, game):
        self.in_loop(self._game_started)

    def _on_game_end(self):
        self.in_loop(self._game_ended)

    def _game_started(self):
        self.refresh_pages()
        self._apply_game_color()

    def _game_ended(self):
        self.refresh_pages()
        self._restore_leds()

    def _apply_game_color(self):
        leds = self.addon('ws2812')
        game = self.games.game
        if leds is None or game is None:
            return
        if not settings.get(self.system, 'rgb_system_colors'):
            self._restore_leds()
            return
        color = colors.color_for(game.system_id, self.systems)
        if color is None:
            self._restore_leds()
            return
        style = self.system.get('rgb_style')
        override = {'rgb_color': color}
        if style in COLORLESS_STYLES:
            override['rgb_style'] = 'breathing'
        leds.update_config(override)  # not saved: back to normal after the game

    def _restore_leds(self):
        leds = self.addon('ws2812')
        if leds is not None:
            leds.update_config({k: self.system[k] for k in ('rgb_color', 'rgb_style')
                                if k in self.system})
