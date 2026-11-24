"""Location slots from add-on settings. Pure: settings are read through a
``get(key) -> str`` callable so this can be tested without Kodi."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

SLOTS = 5

# observation stations per location, in priority order: each current value
# comes from the first station that reports it, then from the forecast
STATIONS = 5

# settings key prefix of each station row: loc{n}_station{i}_{id,name,lat,lon}
STATION_ROLES = tuple(f'station{i}' for i in range(1, STATIONS + 1))

# roles of the pick/clear settings buttons; the station rows have their own
# list editor (settings_ui.edit_stations)
ROLES = ('forecast',)

# forecast point source (loc{n}_fc_source)
FC_STATION, FC_OTHER_STATION, FC_CUSTOM = 0, 1, 2


def key(slot: int, name: str) -> str:
    """Settings id of ``name`` in location ``slot``, e.g. ``loc1_station2_id``."""
    return f'loc{slot}_{name}'


# settings written by the station picker, per role: (id, name, lat, lon)
ROLE_KEYS = {
    'forecast': ('fc_id', 'fc_name', 'fc_lat', 'fc_lon'),
}

# read-only settings line listing the station names, written with the rows
STATIONS_SUMMARY = 'stations_summary'

STATION_FIELDS = ('id', 'name', 'lat', 'lon')


def parse_coord(value: str, limit: float) -> float | None:
    """``value`` as a float within [-limit, limit] (comma decimals accepted),
    or None if it does not parse or is out of range."""
    try:
        v = float(str(value).strip().replace(',', '.'))
    except ValueError:
        return None
    return v if -limit <= v <= limit else None


@dataclass
class Slot:
    """One configured location."""
    index: int                      # 1..SLOTS, settings slot number
    name: str
    station_ids: list[str | None]   # always STATIONS long, None for empty rows
    forecast_lat: float | None
    forecast_lon: float | None

    @property
    def has_stations(self) -> bool:
        """True if at least one observation station is configured."""
        return any(self.station_ids)

    @property
    def has_forecast_point(self) -> bool:
        """True if both forecast coordinates are known."""
        return self.forecast_lat is not None and self.forecast_lon is not None


@dataclass
class StationRow:
    """One observation station row as stored in the settings. Values are the
    stored strings, kept verbatim so a read/write round trip changes nothing."""
    id: str
    name: str = ''
    lat: str = ''
    lon: str = ''


def read_station_rows(get: Callable[[str], str], n: int) -> list[StationRow]:
    """The station rows of slot ``n`` in priority order, empty rows dropped."""
    g = _slot_getter(get, n)
    rows = [StationRow(*(g(f'{role}_{f}') for f in STATION_FIELDS)) for role in STATION_ROLES]
    return [r for r in rows if r.id]


def write_station_rows(set_: Callable[[str, str], None], n: int, rows: list[StationRow]) -> None:
    """Store ``rows`` (at most STATIONS) as rows 1..len(rows) of slot ``n``,
    clear the rows after them and update the summary line."""
    # Rows are always written densely from row 1, so editing never leaves gaps
    # (read_slot would skip them, but a dense list is what the editor shows).
    # Every row up to STATIONS is written, so a row that moved up or was
    # removed does not linger in its old position.
    if len(rows) > STATIONS:
        raise ValueError(f'at most {STATIONS} stations, got {len(rows)}')
    for i, role in enumerate(STATION_ROLES):
        row = rows[i] if i < len(rows) else StationRow('')
        for f in STATION_FIELDS:
            set_(key(n, f'{role}_{f}'), getattr(row, f))
    set_(key(n, STATIONS_SUMMARY), ', '.join(r.name or r.id for r in rows))


def _first_station(g: Callable[[str], str]) -> str | None:
    """Role of the first station row that has an id (rows may have gaps),
    or None if no station is configured. ``g`` reads a slot-local setting."""
    return next((role for role in STATION_ROLES if g(f'{role}_id')), None)


def _station_position(g: Callable[[str], str]) -> tuple[float, float] | None:
    """Coordinates of the first configured station, or None if there is no
    station or its stored coordinates are invalid."""
    role = _first_station(g)
    if role is None:
        return None
    lat, lon = parse_coord(g(f'{role}_lat'), 90), parse_coord(g(f'{role}_lon'), 180)
    return (lat, lon) if lat is not None and lon is not None else None


def _slot_getter(get: Callable[[str], str], n: int) -> Callable[[str], str]:
    """Reader for the settings of slot ``n``: unprefixed name -> stripped value."""
    return lambda name: (get(key(n, name)) or '').strip()


def station_position(get: Callable[[str], str], n: int) -> tuple[float, float] | None:
    """Coordinates of slot ``n``'s first configured station, or None."""
    return _station_position(_slot_getter(get, n))


def read_slot(get: Callable[[str], str], n: int) -> Slot | None:
    """The slot's configuration, or None if it is not configured."""
    # A slot is usable with stations only (no forecast), a forecast point only
    # (no current observations) or both. The station rows are kept as a fixed
    # array with None for empty rows so the priority of each row is explicit;
    # the "first station" (for the default name and the default forecast
    # point) is the first non-empty row, so gaps left by clearing a row are
    # harmless.
    g = _slot_getter(get, n)
    station_ids = [g(f'{role}_id') or None for role in STATION_ROLES]

    # forecast point: from the source selected in settings
    source = int(g('fc_source')) if g('fc_source').isdigit() else FC_STATION
    if source == FC_CUSTOM:
        lat, lon = parse_coord(g('lat'), 90), parse_coord(g('lon'), 180)
    elif source == FC_OTHER_STATION:
        lat, lon = parse_coord(g('fc_lat'), 90), parse_coord(g('fc_lon'), 180)
    else:
        lat, lon = _station_position(g) or (None, None)
    if lat is None or lon is None:
        lat = lon = None

    if not any(station_ids) and lat is None:
        return None
    first = _first_station(g)
    name = g('name') or (first and g(f'{first}_name')) or f'Location {n}'
    return Slot(n, name, station_ids, lat, lon)


def configured_slots(get: Callable[[str], str]) -> list[Slot]:
    """Configured slots in order. Kodi location index k (1-based) maps to
    element k-1, so unconfigured slots leave no gaps in Kodi's list."""
    return [s for n in range(1, SLOTS + 1) if (s := read_slot(get, n)) is not None]
