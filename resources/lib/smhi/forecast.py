"""SMHI point forecast, snow1g v1.

API: https://opendata.smhi.se/metfcst/snow1gv1
Steps are hourly for the first ~2.5 days, then 3, 6 and 12 hours, up to 10
days ahead. Precipitation is an *amount* over the step's interval
(``intervalParametersStartTime`` .. ``time``), not an intensity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import http, log
from .model import WxObs
from .symbols import Wsymb2, precip_from_ptype

URL = ('https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1'
       '/geotype/point/lon/{lon}/lat/{lat}/data.json')

# 9999 = missing value, -9 = not applicable (e.g. frozen part with no precip)
_MISSING = (9999, -9)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _val(data: dict, key: str, cast=float):
    v = data.get(key)
    if v is None or v in _MISSING:
        return None
    try:
        return cast(v)
    except (TypeError, ValueError):
        return None


def _int(v) -> int:
    return int(round(float(v)))


def parse(doc: dict) -> list[WxObs]:
    """Convert a snow1g data.json document to a time-ordered list of steps."""
    try:
        lon, lat = (float(x) for x in doc['geometry']['coordinates'][:2])
    except (KeyError, TypeError, ValueError):
        lon = lat = None

    steps = []
    for ts in doc.get('timeSeries') or []:
        t = parse_time(ts.get('time'))
        if t is None:
            continue
        start = parse_time(ts.get('intervalParametersStartTime')) or t - timedelta(hours=1)
        hours = (t - start).total_seconds() / 3600 or 1.0
        d = ts.get('data') or {}

        amount = _val(d, 'precipitation_amount_mean')
        cloud = _val(d, 'cloud_area_fraction', _int)
        steps.append(WxObs(
            time=t,
            lat=lat,
            lon=lon,
            temperature=_val(d, 'air_temperature'),
            humidity=_val(d, 'relative_humidity', _int),
            wind_speed=_val(d, 'wind_speed'),
            wind_degree=_val(d, 'wind_from_direction', _int),
            wind_gust=_val(d, 'wind_speed_of_gust'),
            pressure=_val(d, 'air_pressure_at_mean_sea_level'),
            visibility=_val(d, 'visibility_in_air'),
            cloud_cover=cloud if cloud is not None and 0 <= cloud <= 8 else None,
            precip_amount=amount,
            precip_intensity=amount / hours if amount is not None else None,
            precip_type=precip_from_ptype(_val(d, 'predominant_precipitation_type_at_surface', _int)),
            thunder_prob=_val(d, 'thunderstorm_probability', _int),
            symbol=Wsymb2.parse(_val(d, 'symbol_code', _int)),
            interval_hours=hours,
            source='forecast',
        ))
    steps.sort(key=lambda s: s.time)
    return steps


def get_forecast(lat: float, lon: float) -> list[WxObs] | None:
    """Fetch the forecast for a point. Returns None on failure."""
    url = URL.format(lat=round(lat, 4), lon=round(lon, 4))
    status, doc = http.get_json(url)
    if status == 404:
        log.warning(f'no forecast for lat {lat}, lon {lon}: point is outside '
                    f"SMHI's forecast area")
        return None
    if doc is None:
        log.warning(f'forecast request failed (HTTP {status}) for lat {lat}, lon {lon}')
        return None
    steps = parse(doc)
    log.debug(f'forecast: {len(steps)} steps for lat {lat}, lon {lon}')
    return steps or None


def step_at(steps: list[WxObs] | None, when: datetime) -> WxObs | None:
    """The forecast step whose interval contains ``when``, else the nearest."""
    if not steps:
        return None
    for s in steps:
        start = s.time - timedelta(hours=s.interval_hours or 1)
        if start <= when <= s.time:
            return s
    return min(steps, key=lambda s: abs((s.time - when).total_seconds()))
