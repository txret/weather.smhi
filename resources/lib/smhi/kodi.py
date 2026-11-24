"""Kodi glue: settings, the weather window, region-aware formatting."""
from __future__ import annotations

import os
from datetime import date, datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import ADDON_ID, props
from .symbols import string_id

WEATHER_WINDOW = 12600
S_MOON_PHASE = 32070  # strings.po: 32070 new moon .. 32077 waning crescent


def addon() -> xbmcaddon.Addon:
    return xbmcaddon.Addon(ADDON_ID)


def get_setting(key: str) -> str:
    return addon().getSetting(key)


def set_setting(key: str, value: str) -> None:
    addon().setSetting(key, value)


def localize(string_id_: int, default: str = '') -> str:
    return addon().getLocalizedString(string_id_) or default


def profile_dir() -> str:
    path = xbmcvfs.translatePath(addon().getAddonInfo('profile'))
    os.makedirs(path, exist_ok=True)
    return path


def window() -> xbmcgui.Window:
    return xbmcgui.Window(WEATHER_WINDOW)


def write_props(values: dict[str, str]) -> None:
    """Set ``values`` on the weather window and clear every other property
    this add-on owns, so nothing stale survives from a previous location."""
    win = window()
    for k in props.all_keys():
        if k in values:
            win.setProperty(k, values[k])
        else:
            win.clearProperty(k)


def write_locations(names: list[str], max_slots: int) -> None:
    win = window()
    win.setProperty('Locations', str(len(names)))
    for i in range(1, max_slots + 1):
        if i <= len(names):
            win.setProperty(f'Location{i}', names[i - 1])
        else:
            win.clearProperty(f'Location{i}')


# ------------------------------------------------------------- formatting

# Kodi's region unit strings -> factor from m/s
_SPEED = {
    'km/h': 3.6, 'm/min': 60.0, 'm/s': 1.0, 'ft/h': 11811.0236, 'ft/min': 196.850394,
    'ft/s': 3.2808399, 'mph': 2.23693629, 'kts': 1.94384449, 'inch/s': 39.3700787,
    'yard/s': 1.0936133, 'Furlong/Fortnight': 6012.88475,
}
# Beaufort upper limits in m/s for force 0..11; above is 12
_BEAUFORT = (0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7)

_TEMP = {
    '°C': lambda c: c,
    '°F': lambda c: c * 1.8 + 32,
    'K': lambda c: c + 273.15,
    '°Ré': lambda c: c * 0.8,
    '°Ra': lambda c: (c + 273.15) * 1.8,
    '°Rø': lambda c: c * 0.525 + 7.5,
    '°De': lambda c: (100 - c) * 1.5,
    '°N': lambda c: c * 0.33,
}

# Kodi core strings: 11–17 Monday..Sunday, 41–47 Mon..Sun,
# 21–32 January..December, 51–62 Jan..Dec, 71–86 compass N..NNW
_LONG_DAY, _SHORT_DAY, _LONG_MONTH, _SHORT_MONTH, _COMPASS = 11, 41, 21, 51, 71
_COMPASS_ORDER = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')


def _kodi_string(sid: int, default: str) -> str:
    return xbmc.getLocalizedString(sid) or default


def speed_in(ms: float, unit: str) -> tuple[float, str]:
    """Convert m/s to Kodi's ``unit``; unknown units fall back to km/h."""
    if unit == 'Beaufort':
        return float(next((i for i, lim in enumerate(_BEAUFORT) if ms < lim), 12)), 'Beaufort'
    if unit in _SPEED:
        return ms * _SPEED[unit], unit
    return ms * 3.6, 'km/h'


def temp_in(c: float, unit: str) -> tuple[float, str]:
    """Convert °C to Kodi's ``unit``; unknown units fall back to °C."""
    conv = _TEMP.get(unit)
    return (conv(c), unit) if conv else (c, '°C')


class KodiFormatter(props.Formatter):
    """Formats extended properties per the user's Kodi region settings."""

    def __init__(self):
        super().__init__(tz=None)  # Kodi's local time zone
        self.temp_unit = xbmc.getRegion('tempunit')
        self.speed_unit = xbmc.getRegion('speedunit')
        self.time_fmt = (xbmc.getRegion('time') or '%H:%M:%S').replace(':%S', '')
        self.short_date_fmt = xbmc.getRegion('dateshort') or '%d/%m/%Y'
        self.long_date_fmt = xbmc.getRegion('datelong') or '%A, %d %B %Y'

    def _strftime(self, dt, fmt: str) -> str:
        # Python's %A/%B depend on the C locale; use Kodi's localized names
        wd, m = dt.weekday(), dt.month - 1
        fmt = (fmt.replace('%A', _kodi_string(_LONG_DAY + wd, '%A'))
                  .replace('%a', _kodi_string(_SHORT_DAY + wd, '%a'))
                  .replace('%B', _kodi_string(_LONG_MONTH + m, '%B'))
                  .replace('%b', _kodi_string(_SHORT_MONTH + m, '%b')))
        return dt.strftime(fmt)

    def temp(self, c: float) -> str:
        v, unit = temp_in(c, self.temp_unit)
        return f'{round(v)}{unit}'

    def speed(self, ms: float) -> str:
        v, unit = speed_in(ms, self.speed_unit)
        return f'{round(v)} {unit}'

    def time(self, dt: datetime) -> str:
        return self._strftime(self.local(dt), self.time_fmt)

    def short_date(self, d: date) -> str:
        return self._strftime(d, self.short_date_fmt)

    def long_date(self, d: date) -> str:
        return self._strftime(d, self.long_date_fmt)

    def short_day(self, d: date) -> str:
        return _kodi_string(_SHORT_DAY + d.weekday(), super().short_day(d))

    def long_day(self, d: date) -> str:
        return _kodi_string(_LONG_DAY + d.weekday(), super().long_day(d))

    def wind_direction(self, abbrev: str) -> str:
        if abbrev in _COMPASS_ORDER:
            return _kodi_string(_COMPASS + _COMPASS_ORDER.index(abbrev), abbrev)
        return abbrev

    def moon_phase(self, index: int) -> str:
        return localize(S_MOON_PHASE + index, super().moon_phase(index))

    def condition(self, symbol, fallback):
        if symbol is None:
            return fallback
        return localize(string_id(symbol), super().condition(symbol, fallback))
