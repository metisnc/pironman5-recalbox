# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
"""OLED additions: short messages over the pages and a "now playing" page.

pm_auto builds its pages with pm_auto.addons.oled.get_pages(); install()
replaces that function so every page is wrapped (messages are drawn over
any page) and the extra 'game' page name is understood.
"""
import time

from pm_auto.libs.oled_page import OLEDPage
from pm_auto.libs.utils import get_font

FONT = get_font('UbuntuSans-Regular.ttf')
WIDTH = 128
GAME_PAGE = 'game'


class Toast:
    """Message shown over the current page for a few seconds."""

    def __init__(self):
        self.lines = []
        self.until = 0

    def show(self, lines, duration=3):
        self.lines = [str(line) for line in lines if line is not None]
        self.until = time.time() + duration

    def active(self):
        return bool(self.lines) and time.time() < self.until

    def draw(self, oled):
        oled.clear()
        if len(self.lines) <= 2:
            title = self.lines[0] if self.lines else ''
            value = self.lines[1] if len(self.lines) > 1 else ''
            oled.draw_text(fit(title, 13), WIDTH // 2, 8, align='center', size=13, font_path=FONT)
            oled.draw_text(fit(value, 16), WIDTH // 2, 32, align='center', size=16, font_path=FONT)
        else:
            for i, line in enumerate(self.lines[:5]):
                oled.draw_text(fit(line, 11), 0, i * 12, size=11, font_path=FONT)
        oled.display()


def text_width(text, size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, size).getlength(text)


def fit(text, size, width=WIDTH):
    """Truncate text with an ellipsis so it fits in width pixels."""
    if text_width(text, size) <= width:
        return text
    while text and text_width(text + '…', size) > width:
        text = text[:-1]
    return text.rstrip() + '…'


def wrap(text, size, width=WIDTH, max_lines=2):
    """Word wrap on max_lines lines, the last one truncated."""
    words, lines, current = text.split(), [], ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if text_width(candidate, size) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [' '.join(lines[max_lines - 1:])]
    return [fit(line, size, width) for line in lines]


def format_elapsed(seconds):
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f'{hours}:{minutes:02d}:{secs:02d}' if hours else f'{minutes}:{secs:02d}'


class GamePage(OLEDPage):
    """System, title, play time, CPU, RAM and temperature of the running game."""

    def __init__(self, get_game):
        super().__init__()
        self.get_game = get_game

    def main(self, oled, data, config):
        game = self.get_game()
        oled.clear()
        if game is None:
            oled.display()
            return
        elapsed = format_elapsed(game.elapsed())
        oled.draw_text(elapsed, WIDTH, 0, align='right', size=11, font_path=FONT)
        system_width = WIDTH - text_width(elapsed, 11) - 4
        oled.draw_text(fit(game.system, 11, system_width), 0, 0, size=11, font_path=FONT)
        for i, line in enumerate(wrap(game.title, 14)):
            oled.draw_text(line, 0, 14 + i * 16, size=14, font_path=FONT)

        unit = config.get('temperature_unit', 'C')
        temp = data.get('cpu_temperature', 0) or 0
        if unit == 'F':
            temp = temp * 9 / 5 + 32
        cpu = min(int(data.get('cpu_percent', 0) or 0), 100)
        ram = min(int(data.get('memory_percent', 0) or 0), 100)
        oled.draw_text(fit(f'CPU {cpu}%  RAM {ram}%  {int(temp)}°{unit}', 11),
                       WIDTH // 2, 51, align='center', size=11, font_path=FONT)
        oled.display()


class Overlay(OLEDPage):
    """Wraps a pm_auto page: draws the toast instead of the page when active."""

    def __init__(self, page, toast):
        super().__init__()
        self.page = page
        self.toast = toast

    def __getattr__(self, name):  # needs_ip and other page attributes
        return getattr(self.page, name)

    def main(self, oled, *args, **kwargs):
        if self.toast.active():
            self.toast.draw(oled)
        else:
            self.page.main(oled, *args, **kwargs)

    def __str__(self):
        return str(self.page)


def install(toast, get_game):
    """Make pm_auto's OLED addon build wrapped pages and know the game page."""
    import pm_auto.addons.oled as oled_addon
    upstream_get_pages = oled_addon.get_pages

    def get_pages(page_names):
        pages = []
        for name in page_names:
            if name == GAME_PAGE:
                page = GamePage(get_game)
            else:
                page = upstream_get_pages([name])[0]
            pages.append(Overlay(page, toast))
        return pages

    oled_addon.get_pages = get_pages
