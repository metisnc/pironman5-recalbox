# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""Game start/stop detection from EmulationStation's state file."""
import os
import threading
import time

ES_STATE = '/tmp/es_state.inf'
GAME_START = {'rungame', 'rundemo'}
# Browsing actions also end a game, in case an endgame event was missed
GAME_END = {'endgame', 'enddemo', 'stop', 'quit', 'shutdown', 'reboot',
            'gamelistbrowsing', 'systembrowsing'}
SLEEP = 'sleep'  # screensaver; any later action means awake again


def parse_state(content):
    state = {}
    for line in content.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            state[key.strip()] = value.strip()
    return state


def read_state(path=ES_STATE):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return parse_state(f.read())
    except OSError:
        return {}


class Game:
    def __init__(self, state):
        self.system = state.get('System', '')
        self.system_id = state.get('SystemId', '')
        self.title = state.get('Game', '') or os.path.basename(state.get('GamePath', ''))
        self.publisher = state.get('Publisher', '') or state.get('Developer', '')
        self.started = time.time()

    def elapsed(self):
        return int(time.time() - self.started)


class GameWatcher:
    """Calls on_start(Game) / on_end() when a game starts or stops, and
    on_sleep() / on_wake() around the EmulationStation screensaver."""

    def __init__(self, on_start, on_end, log, path=ES_STATE, interval=0.5,
                 on_sleep=None, on_wake=None):
        self.on_start = on_start
        self.on_end = on_end
        self.on_sleep = on_sleep or (lambda: None)
        self.on_wake = on_wake or (lambda: None)
        self.log = log
        self.path = path
        self.interval = interval
        self.game = None
        self.sleeping = False
        self._mtime = None
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run, name='es-events', daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stopping.set()
        self._thread.join()

    def poll(self):
        try:
            mtime = os.stat(self.path).st_mtime
        except OSError:
            return
        if mtime == self._mtime:
            return
        self._mtime = mtime
        state = read_state(self.path)
        action = state.get('Action', '')
        if action == SLEEP and not self.sleeping:
            self.sleeping = True
            self.log.info('EmulationStation screensaver started')
            self.on_sleep()
        elif action != SLEEP and self.sleeping:
            # wakeup, or any other action: EmulationStation is awake again
            self.sleeping = False
            self.log.info('EmulationStation woke up')
            self.on_wake()
        if action in GAME_START and self.game is None:
            self.game = Game(state)
            self.log.info('Game started: %s / %s', self.game.system, self.game.title)
            self.on_start(self.game)
        elif action in GAME_END and self.game is not None:
            self.log.info('Game ended: %s', self.game.title)
            self.game = None
            self.on_end()

    def _run(self):
        while not self._stopping.wait(self.interval):
            try:
                self.poll()
            except Exception:
                self.log.exception('EmulationStation event error')
