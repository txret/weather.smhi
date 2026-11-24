"""SMHI meteorological observations (metobs).

API: https://opendata.smhi.se/metobs
Each parameter is a separate resource; a station that does not measure a
parameter answers 404 for it.
"""
from __future__ import annotations

import json
import math
import os
import time as _time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from . import http, log
from .model import WxObs

BASE = 'https://opendata-download-metobs.smhi.se/api/version/latest/parameter/{param}'
STATION_URL = BASE + '/station/{station}/period/latest-hour/data.json'
STATION_SET_URL = BASE + '/station-set/all/period/latest-hour/data.json'

MAX_AGE = timedelta(hours=2)
STATION_CACHE_TTL = 7 * 24 * 3600  # seconds
STATION_CACHE_FILE = 'stations.json'

# Parameters used for the station list: a station reporting either one right
# now is considered active.
STATION_LIST_PARAMS = (1, 4)


def _octas_from_percent(v: float) -> int:
    return max(0, min(8, round(v / 12.5)))


# param -> (WxObs field, conversion of the raw float)
PARAMS: dict[int, tuple[str, object]] = {
    1: ('temperature', float),                     # Lufttemperatur, °C
    3: ('wind_degree', lambda v: int(round(v))),   # Vindriktning, degrees
    4: ('wind_speed', float),                      # Vindhastighet, m/s
    6: ('humidity', lambda v: int(round(v))),      # Relativ luftfuktighet, %
    9: ('pressure', float),                        # Lufttryck havsytans nivå, hPa
    12: ('visibility', lambda v: v / 1000),        # Sikt, m -> km
    14: ('precip_intensity', None),                # Nederbörd 15 min, summed -> mm/h
    16: ('cloud_cover', _octas_from_percent),      # Total molnmängd, % -> octas
    21: ('wind_gust', float),                      # Byvind, max, m/s
    39: ('dew_point', float),                      # Daggpunktstemperatur, °C
}


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    lat: float
    lon: float

    def distance_km(self, lat: float, lon: float) -> float:
        return haversine_km(self.lat, self.lon, lat, lon)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _fresh_values(values, now: datetime) -> list[tuple[datetime, float]]:
    """[(time, value)] for values that parse and are not older than MAX_AGE."""
    out = []
    for v in values or []:
        try:
            t = datetime.fromtimestamp(v['date'] / 1000, tz=timezone.utc)
            x = float(v['value'])
        except (KeyError, TypeError, ValueError):
            continue
        if now - t <= MAX_AGE:
            out.append((t, x))
    out.sort(key=lambda tv: tv[0])
    return out


def _fetch_param(station_id: str, param: int) -> dict | None:
    status, doc = http.get_json(STATION_URL.format(param=param, station=station_id))
    if status == 404:
        log.debug(f'station {station_id} does not report parameter {param}')
    elif doc is None:
        log.warning(f'station {station_id}, parameter {param}: request failed (HTTP {status})')
    return doc


def get_station_obs(station_id: str, now: datetime | None = None) -> WxObs | None:
    """Latest observation from one station, or None if it reported nothing."""
    now = now or datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=len(PARAMS)) as pool:
        docs = dict(zip(PARAMS, pool.map(lambda p: _fetch_param(station_id, p), PARAMS)))

    obs = WxObs()
    latest: datetime | None = None
    for param, doc in docs.items():
        if not doc:
            continue
        if obs.lat is None:
            pos = (doc.get('position') or [{}])[-1]
            obs.lat, obs.lon = pos.get('latitude'), pos.get('longitude')
            obs.source = (doc.get('station') or {}).get('name')
        values = _fresh_values(doc.get('value'), now)
        if not values:
            continue
        field, conv = PARAMS[param]
        if param == 14:
            # 15-minute sums: total over the last hour = mm/h
            hour = [x for t, x in values if values[-1][0] - t < timedelta(hours=1)]
            value = sum(hour) * 4 / len(hour)
        else:
            value = conv(values[-1][1])
        setattr(obs, field, value)
        latest = max(latest, values[-1][0]) if latest else values[-1][0]

    if latest is None:
        log.warning(f'station {station_id}: no recent observations')
        return None
    obs.time = latest
    return obs


# ----------------------------------------------------------------- stations

def _download_stations() -> list[Station] | None:
    stations: dict[str, Station] = {}
    for param in STATION_LIST_PARAMS:
        _, doc = http.get_json(STATION_SET_URL.format(param=param), timeout=30)
        if not doc:
            continue
        for s in doc.get('station') or []:
            try:
                st = Station(str(s['key']), s['name'], float(s['latitude']), float(s['longitude']))
            except (KeyError, TypeError, ValueError):
                continue
            if s.get('value'):
                stations.setdefault(st.id, st)
    if not stations:
        return None
    return sorted(stations.values(), key=lambda s: s.name.lower())


def list_stations(cache_dir: str | None = None, max_age: float = STATION_CACHE_TTL) -> list[Station] | None:
    """Active SMHI stations, cached on disk in ``cache_dir`` for ``max_age`` s."""
    path = os.path.join(cache_dir, STATION_CACHE_FILE) if cache_dir else None
    cached = None
    if path and os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                cached = [Station(**s) for s in json.load(f)]
        except (OSError, ValueError, TypeError) as e:
            log.warning(f'ignoring broken station cache: {e}')
        if cached and _time.time() - os.path.getmtime(path) < max_age:
            return cached

    stations = _download_stations()
    if stations is None:
        return cached  # stale cache beats nothing
    if path:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump([asdict(s) for s in stations], f)
        except OSError as e:
            log.warning(f'could not write station cache: {e}')
    return stations
