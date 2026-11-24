"""Build the Kodi weather window properties. Pure: no Kodi imports.

Two groups of properties are produced:

* **Core** properties, read by Kodi itself (``Current.*``, ``Day0..6.*``).
  These hold *raw metric numbers* (°C, km/h) and *English* text; Kodi
  converts units and localizes words for the user.
* **Extended** properties (``Today.*``, ``Hourly.N.*``, ``Daily.N.*`` and
  extra ``Current.*``), read directly by skins. These are formatted and localized
  by the add-on through a :class:`Formatter`.
"""
from __future__ import annotations

from datetime import datetime, timezone, tzinfo

from .daily import DaySummary
from .model import MOON_PHASES, WxObs, moon_phase, sun_times
from .symbols import TEXT as SYMBOL_TEXT, fanart_code, outlook_icon

CORE_DAYS = 7          # Day0..Day6, fixed by Kodi
MAX_HOURLY = 48
MAX_DAILY = 10

ENGLISH_DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')

CURRENT_KEYS = ('Location', 'Condition', 'Temperature', 'Wind', 'WindDirection',
                'Humidity', 'FeelsLike', 'DewPoint', 'UVIndex', 'OutlookIcon',
                'FanartCode', 'SymbolCode', 'Precipitation', 'Pressure', 'Visibility',
                'Cloudiness', 'WindGust', 'ObservationTime', 'Station', 'IsFetched')
TODAY_KEYS = ('Sunrise', 'Sunset', 'Moonphase', 'IsFetched')
DAY_KEYS = ('Title', 'HighTemp', 'LowTemp', 'Outlook', 'OutlookIcon', 'FanartCode')
HOURLY_KEYS = ('Time', 'ShortDate', 'LongDate', 'Outlook', 'OutlookIcon', 'FanartCode',
               'SymbolCode', 'Temperature', 'FeelsLike', 'Humidity', 'Precipitation',
               'WindSpeed', 'WindDirection', 'WindDegree', 'DewPoint', 'Pressure')
DAILY_KEYS = ('ShortDay', 'LongDay', 'ShortDate', 'LongDate', 'Outlook', 'OutlookIcon',
              'FanartCode', 'SymbolCode', 'HighTemperature', 'LowTemperature',
              'WindSpeed', 'WindDirection', 'Precipitation', 'Humidity',
              'Sunrise', 'Sunset')
OTHER_KEYS = ('Hourly.IsFetched', 'Daily.IsFetched', 'Forecast.City',
              'Forecast.Updated', 'WeatherProvider')


def all_keys() -> list[str]:
    """Every property this add-on may set; anything not set is cleared."""
    keys = [f'Current.{k}' for k in CURRENT_KEYS]
    keys += [f'Today.{k}' for k in TODAY_KEYS]
    keys += [f'Day{i}.{k}' for i in range(CORE_DAYS) for k in DAY_KEYS]
    keys += [f'Hourly.{i}.{k}' for i in range(1, MAX_HOURLY + 1) for k in HOURLY_KEYS]
    keys += [f'Daily.{i}.{k}' for i in range(1, MAX_DAILY + 1) for k in DAILY_KEYS]
    keys += list(OTHER_KEYS)
    return keys


class Formatter:
    """Formatting for extended properties: metric, English, local time.

    ``smhi.kodi.KodiFormatter`` overrides this with the user's Kodi region
    settings (units, date/time formats) and localized strings.
    """

    def __init__(self, tz: tzinfo | None = None):
        self.tz = tz

    def local(self, dt: datetime) -> datetime:
        return dt.astimezone(self.tz)

    def temp(self, c: float) -> str: return f'{round(c)}°C'
    def speed(self, ms: float) -> str: return f'{round(ms * 3.6)} km/h'
    def precip(self, mm: float) -> str: return f'{mm:.1f} mm'
    def pressure(self, hpa: float) -> str: return f'{round(hpa)} hPa'
    def distance(self, km: float) -> str: return f'{km:.0f} km' if km >= 10 else f'{km:.1f} km'
    def time(self, dt: datetime) -> str: return self.local(dt).strftime('%H:%M')
    def short_date(self, dt) -> str: return dt.strftime('%d/%m')
    def long_date(self, dt) -> str: return f'{dt.day} {dt.strftime("%B")}'
    def short_day(self, dt) -> str: return ENGLISH_DAYS[dt.weekday()][:3]
    def long_day(self, dt) -> str: return ENGLISH_DAYS[dt.weekday()]
    def wind_direction(self, abbrev: str) -> str: return abbrev
    def moon_phase(self, index: int) -> str: return MOON_PHASES[index]

    def condition(self, symbol, fallback: str | None) -> str | None:
        return SYMBOL_TEXT[symbol] if symbol is not None else fallback


def _num(x: float | None) -> str | None:
    return str(round(x)) if x is not None else None


def build(location: str, current: WxObs | None, steps: list[WxObs] | None,
          days: list[DaySummary] | None, fmt: Formatter | None = None,
          now: datetime | None = None) -> dict[str, str]:
    """Return {property: value}. Missing values are omitted, never None."""
    fmt = fmt or Formatter()
    now = now or datetime.now(timezone.utc)
    p: dict[str, str | None] = {'WeatherProvider': 'SMHI', 'Forecast.City': location,
                                'Forecast.Updated': fmt.time(now)}

    if current is not None:
        _current(p, location, current, fmt)
        _today(p, current, fmt, now)

    days = days or []
    for i, day in enumerate(days[:CORE_DAYS]):
        _core_day(p, i, day)
    for i, day in enumerate(days[:MAX_DAILY], start=1):
        _daily(p, i, day, fmt)
    if days:
        p['Daily.IsFetched'] = 'true'

    hourly = [s for s in steps or []
              if s.time > now and (s.interval_hours or 1) <= 1][:MAX_HOURLY]
    for i, step in enumerate(hourly, start=1):
        _hourly(p, i, step, fmt)
    if hourly:
        p['Hourly.IsFetched'] = 'true'

    return {k: v for k, v in p.items() if v is not None and v != ''}


def _icon_props(p: dict, prefix: str, symbol, night: bool) -> None:
    code = fanart_code(symbol, night)
    p[f'{prefix}.OutlookIcon'] = outlook_icon(code)
    p[f'{prefix}.FanartCode'] = str(code) if code is not None else None
    p[f'{prefix}.SymbolCode'] = str(int(symbol)) if symbol is not None else None


def _current(p: dict, location: str, c: WxObs, fmt: Formatter) -> None:
    pre = 'Current'
    # core (raw metric / English)
    p[f'{pre}.Location'] = location
    p[f'{pre}.Condition'] = c.condition_text
    p[f'{pre}.Temperature'] = _num(c.temperature)
    p[f'{pre}.FeelsLike'] = _num(c.feels_like)
    p[f'{pre}.DewPoint'] = _num(c.dew_point)
    p[f'{pre}.Humidity'] = _num(c.humidity)
    p[f'{pre}.Wind'] = _num(c.wind_speed * 3.6) if c.wind_speed is not None else None
    p[f'{pre}.WindDirection'] = 'CALM' if c.calm else c.wind_direction
    _icon_props(p, pre, c.effective_symbol, c.night)
    # extended (formatted)
    if c.precip_intensity is not None:
        p[f'{pre}.Precipitation'] = fmt.precip(c.precip_intensity)
    if c.pressure is not None:
        p[f'{pre}.Pressure'] = fmt.pressure(c.pressure)
    if c.visibility is not None:
        p[f'{pre}.Visibility'] = fmt.distance(c.visibility)
    if c.cloud_cover is not None:
        p[f'{pre}.Cloudiness'] = f'{round(c.cloud_cover * 12.5)}%'
    if c.wind_gust is not None:
        p[f'{pre}.WindGust'] = fmt.speed(c.wind_gust)
    if c.time is not None:
        p[f'{pre}.ObservationTime'] = fmt.time(c.time)
    if c.source and c.source != 'forecast':
        p[f'{pre}.Station'] = c.source
    p[f'{pre}.IsFetched'] = 'true'


def _today(p: dict, c: WxObs, fmt: Formatter, now: datetime) -> None:
    """Today.*: sun and moon for today's local date at the location."""
    today = fmt.local(now).date()
    p['Today.Moonphase'] = fmt.moon_phase(moon_phase(today))
    if c.lat is not None and c.lon is not None:
        sunrise, sunset = sun_times(c.lat, c.lon, today, fmt.tz)
        p['Today.Sunrise'] = fmt.time(sunrise) if sunrise else None
        p['Today.Sunset'] = fmt.time(sunset) if sunset else None
    p['Today.IsFetched'] = 'true'


def _core_day(p: dict, i: int, d: DaySummary) -> None:
    pre = f'Day{i}'
    p[f'{pre}.Title'] = ENGLISH_DAYS[d.date.weekday()]
    p[f'{pre}.HighTemp'] = _num(d.high)
    p[f'{pre}.LowTemp'] = _num(d.low)
    p[f'{pre}.Outlook'] = d.condition_text
    code = fanart_code(d.symbol, False)
    p[f'{pre}.OutlookIcon'] = outlook_icon(code)
    p[f'{pre}.FanartCode'] = str(code) if code is not None else None


def _daily(p: dict, i: int, d: DaySummary, fmt: Formatter) -> None:
    pre = f'Daily.{i}'
    p[f'{pre}.ShortDay'] = fmt.short_day(d.date)
    p[f'{pre}.LongDay'] = fmt.long_day(d.date)
    p[f'{pre}.ShortDate'] = fmt.short_date(d.date)
    p[f'{pre}.LongDate'] = fmt.long_date(d.date)
    p[f'{pre}.Outlook'] = fmt.condition(d.symbol, d.condition_text)
    _icon_props(p, pre, d.symbol, False)
    p[f'{pre}.HighTemperature'] = fmt.temp(d.high) if d.high is not None else None
    p[f'{pre}.LowTemperature'] = fmt.temp(d.low) if d.low is not None else None
    p[f'{pre}.WindSpeed'] = fmt.speed(d.wind_speed) if d.wind_speed is not None else None
    rep_dir = d.representative.wind_direction
    p[f'{pre}.WindDirection'] = fmt.wind_direction(rep_dir) if rep_dir else None
    p[f'{pre}.Precipitation'] = fmt.precip(d.precip_amount) if d.precip_amount is not None else None
    p[f'{pre}.Humidity'] = f'{d.humidity}%' if d.humidity is not None else None
    rep = d.representative
    if rep.lat is not None and rep.lon is not None:
        sunrise, sunset = sun_times(rep.lat, rep.lon, d.date, fmt.tz)
        p[f'{pre}.Sunrise'] = fmt.time(sunrise) if sunrise else None
        p[f'{pre}.Sunset'] = fmt.time(sunset) if sunset else None


def _hourly(p: dict, i: int, s: WxObs, fmt: Formatter) -> None:
    pre = f'Hourly.{i}'
    local = fmt.local(s.time)
    p[f'{pre}.Time'] = fmt.time(s.time)
    p[f'{pre}.ShortDate'] = fmt.short_date(local)
    p[f'{pre}.LongDate'] = fmt.long_date(local)
    p[f'{pre}.Outlook'] = fmt.condition(s.effective_symbol, s.condition_text)
    _icon_props(p, pre, s.effective_symbol, s.night)
    p[f'{pre}.Temperature'] = fmt.temp(s.temperature) if s.temperature is not None else None
    p[f'{pre}.FeelsLike'] = fmt.temp(s.feels_like) if s.feels_like is not None else None
    p[f'{pre}.DewPoint'] = fmt.temp(s.dew_point) if s.dew_point is not None else None
    p[f'{pre}.Humidity'] = f'{s.humidity}%' if s.humidity is not None else None
    p[f'{pre}.Precipitation'] = fmt.precip(s.precip_amount) if s.precip_amount is not None else None
    p[f'{pre}.WindSpeed'] = fmt.speed(s.wind_speed) if s.wind_speed is not None else None
    p[f'{pre}.WindDirection'] = fmt.wind_direction(s.wind_direction) if s.wind_direction else None
    p[f'{pre}.WindDegree'] = f'{s.wind_degree}°' if s.wind_degree is not None else None
    p[f'{pre}.Pressure'] = fmt.pressure(s.pressure) if s.pressure is not None else None
