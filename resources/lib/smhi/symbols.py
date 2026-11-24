"""SMHI weather symbols (Wsymb2), precipitation types and Kodi icon codes."""
from __future__ import annotations

from enum import IntEnum


class Wsymb2(IntEnum):
    """SMHI weather symbol codes, see
    https://www.smhi.se/kunskapsbanken/meteorologi/vaderprognoser/vad-betyder-smhis-vadersymboler-1.12109
    """
    CLEAR = 1
    NEARLY_CLEAR = 2
    VARIABLE_CLOUDINESS = 3
    HALFCLEAR = 4
    CLOUDY = 5
    OVERCAST = 6
    FOG = 7
    LIGHT_RAIN_SHOWERS = 8
    MODERATE_RAIN_SHOWERS = 9
    HEAVY_RAIN_SHOWERS = 10
    THUNDERSTORM = 11
    LIGHT_SLEET_SHOWERS = 12
    MODERATE_SLEET_SHOWERS = 13
    HEAVY_SLEET_SHOWERS = 14
    LIGHT_SNOW_SHOWERS = 15
    MODERATE_SNOW_SHOWERS = 16
    HEAVY_SNOW_SHOWERS = 17
    LIGHT_RAIN = 18
    MODERATE_RAIN = 19
    HEAVY_RAIN = 20
    THUNDER = 21
    LIGHT_SLEET = 22
    MODERATE_SLEET = 23
    HEAVY_SLEET = 24
    LIGHT_SNOWFALL = 25
    MODERATE_SNOWFALL = 26
    HEAVY_SNOWFALL = 27

    @classmethod
    def parse(cls, value) -> 'Wsymb2 | None':
        try:
            return cls(int(value))
        except (TypeError, ValueError):
            return None


# English condition text. Kodi's core weather labels are localized by Kodi
# itself from English words, so the core properties use these strings.
TEXT = {
    Wsymb2.CLEAR: 'Clear sky',
    Wsymb2.NEARLY_CLEAR: 'Nearly clear sky',
    Wsymb2.VARIABLE_CLOUDINESS: 'Variable cloudiness',
    Wsymb2.HALFCLEAR: 'Half clear sky',
    Wsymb2.CLOUDY: 'Cloudy sky',
    Wsymb2.OVERCAST: 'Overcast',
    Wsymb2.FOG: 'Fog',
    Wsymb2.LIGHT_RAIN_SHOWERS: 'Light rain showers',
    Wsymb2.MODERATE_RAIN_SHOWERS: 'Moderate rain showers',
    Wsymb2.HEAVY_RAIN_SHOWERS: 'Heavy rain showers',
    Wsymb2.THUNDERSTORM: 'Thunderstorm',
    Wsymb2.LIGHT_SLEET_SHOWERS: 'Light sleet showers',
    Wsymb2.MODERATE_SLEET_SHOWERS: 'Moderate sleet showers',
    Wsymb2.HEAVY_SLEET_SHOWERS: 'Heavy sleet showers',
    Wsymb2.LIGHT_SNOW_SHOWERS: 'Light snow showers',
    Wsymb2.MODERATE_SNOW_SHOWERS: 'Moderate snow showers',
    Wsymb2.HEAVY_SNOW_SHOWERS: 'Heavy snow showers',
    Wsymb2.LIGHT_RAIN: 'Light rain',
    Wsymb2.MODERATE_RAIN: 'Moderate rain',
    Wsymb2.HEAVY_RAIN: 'Heavy rain',
    Wsymb2.THUNDER: 'Thunder',
    Wsymb2.LIGHT_SLEET: 'Light sleet',
    Wsymb2.MODERATE_SLEET: 'Moderate sleet',
    Wsymb2.HEAVY_SLEET: 'Heavy sleet',
    Wsymb2.LIGHT_SNOWFALL: 'Light snowfall',
    Wsymb2.MODERATE_SNOWFALL: 'Moderate snowfall',
    Wsymb2.HEAVY_SNOWFALL: 'Heavy snowfall',
}

# strings.po id for the localized text of each symbol (32100 + code)
STRING_ID_BASE = 32100


def string_id(symbol: Wsymb2) -> int:
    return STRING_ID_BASE + int(symbol)


# Kodi weather icon / fanart codes (resource.images.weathericons.default):
# 4 thunderstorms, 5 mixed rain and snow, 9 drizzle, 11/12 showers, 14 light
# snow showers, 16 snow, 20 foggy, 26 cloudy, 27/28 mostly cloudy (night/day),
# 29/30 partly cloudy (night/day), 31 clear night, 32 sunny, 33/34 fair
# (night/day), 40 scattered showers, 41 heavy snow, 43 heavy snow, 46 snow showers
_FANART_DAY = {
    Wsymb2.CLEAR: 32,
    Wsymb2.NEARLY_CLEAR: 34,
    Wsymb2.VARIABLE_CLOUDINESS: 30,
    Wsymb2.HALFCLEAR: 28,
    Wsymb2.CLOUDY: 26,
    Wsymb2.OVERCAST: 26,
    Wsymb2.FOG: 20,
    Wsymb2.LIGHT_RAIN_SHOWERS: 40,
    Wsymb2.MODERATE_RAIN_SHOWERS: 11,
    Wsymb2.HEAVY_RAIN_SHOWERS: 12,
    Wsymb2.THUNDERSTORM: 4,
    Wsymb2.LIGHT_SLEET_SHOWERS: 5,
    Wsymb2.MODERATE_SLEET_SHOWERS: 5,
    Wsymb2.HEAVY_SLEET_SHOWERS: 5,
    Wsymb2.LIGHT_SNOW_SHOWERS: 14,
    Wsymb2.MODERATE_SNOW_SHOWERS: 46,
    Wsymb2.HEAVY_SNOW_SHOWERS: 43,
    Wsymb2.LIGHT_RAIN: 9,
    Wsymb2.MODERATE_RAIN: 11,
    Wsymb2.HEAVY_RAIN: 12,
    Wsymb2.THUNDER: 4,
    Wsymb2.LIGHT_SLEET: 5,
    Wsymb2.MODERATE_SLEET: 5,
    Wsymb2.HEAVY_SLEET: 5,
    Wsymb2.LIGHT_SNOWFALL: 14,
    Wsymb2.MODERATE_SNOWFALL: 16,
    Wsymb2.HEAVY_SNOWFALL: 41,
}
_FANART_NIGHT = {
    Wsymb2.CLEAR: 31,
    Wsymb2.NEARLY_CLEAR: 33,
    Wsymb2.VARIABLE_CLOUDINESS: 29,
    Wsymb2.HALFCLEAR: 27,
    Wsymb2.LIGHT_RAIN_SHOWERS: 45,
    Wsymb2.THUNDERSTORM: 47,
}


def fanart_code(symbol: Wsymb2 | None, night: bool = False) -> int | None:
    if symbol is None:
        return None
    if night and symbol in _FANART_NIGHT:
        return _FANART_NIGHT[symbol]
    return _FANART_DAY.get(symbol)


def outlook_icon(code: int | None) -> str | None:
    return f'{code}.png' if code is not None else None


class Precip(IntEnum):
    NONE = 0
    SNOW = 1
    SLEET = 2
    RAIN = 3
    FREEZING_RAIN = 4
    DRIZZLE = 5
    FREEZING_DRIZZLE = 6


# snow1g "predominant_precipitation_type_at_surface" (ECMWF ptype table).
# SMHI's own symbols show wet snow (6) as sleet (dev/symbol_rules); 7 and 8
# never occurred in the analysed data, so their mapping is an assumption.
_PTYPE = {
    0: Precip.NONE,
    1: Precip.RAIN,
    3: Precip.FREEZING_RAIN,
    5: Precip.SNOW,
    6: Precip.SLEET,             # wet snow
    7: Precip.SLEET,             # mixture of rain and snow
    8: Precip.SLEET,             # ice pellets
    11: Precip.DRIZZLE,
    12: Precip.FREEZING_DRIZZLE,
}


def precip_from_ptype(ptype) -> Precip | None:
    """The Precip of a snow1g ptype code, or None for unknown codes."""
    try:
        return _PTYPE.get(int(ptype))
    except (TypeError, ValueError):
        return None
