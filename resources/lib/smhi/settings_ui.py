"""Station dialogs, run from the buttons in the add-on settings: the station
picker and the observation station list editor."""
from __future__ import annotations

import xbmc
import xbmcgui

from . import config, kodi, log
from .observations import Station, haversine_km, list_stations

# strings.po ids
S_STATIONS = 32022
S_SEARCH = 32040
S_LOADING = 32041
S_LOAD_FAILED = 32042
S_NO_MATCH = 32043
S_SELECT = 32044
S_ADD = 32045
S_MOVE_UP = 32046
S_MOVE_DOWN = 32047
S_REPLACE = 32048
S_REMOVE = 32049
S_DUPLICATE = 32050

# station list editor: popup menu actions for a station
MOVE_UP, MOVE_DOWN, REPLACE, REMOVE = 'up', 'down', 'replace', 'remove'


def _reference_point(slot: int) -> tuple[float, float] | None:
    """Where to measure station distances from: the forecast point or the
    first configured station, whichever is known."""
    s = config.read_slot(kodi.get_setting, slot)
    if s and s.has_forecast_point:
        return s.forecast_lat, s.forecast_lon
    return config.station_position(kodi.get_setting, slot)


def _choose(slot: int) -> Station | None:
    """Let the user search for and pick an active SMHI station, sorted by
    distance from the slot's reference point. None if cancelled or failed."""
    dialog = xbmcgui.Dialog()
    query = dialog.input(kodi.localize(S_SEARCH, 'Search stations by name (leave empty for all)'))

    progress = xbmcgui.DialogProgress()
    progress.create('SMHI', kodi.localize(S_LOADING, 'Loading SMHI station list...'))
    try:
        stations = list_stations(kodi.profile_dir())
    finally:
        progress.close()
    if not stations:
        dialog.ok('SMHI', kodi.localize(S_LOAD_FAILED, 'Could not load the SMHI station list.'))
        return None

    q = (query or '').strip().lower()
    if q:
        stations = [s for s in stations if q in s.name.lower() or q == s.id]
        if not stations:
            dialog.ok('SMHI', kodi.localize(S_NO_MATCH, 'No stations match "%s".').replace('%s', query))
            return None

    ref = _reference_point(slot)
    if ref:
        stations = sorted(stations, key=lambda s: s.distance_km(*ref))

    items = []
    for s in stations:
        item = xbmcgui.ListItem(s.name)
        detail = f'id {s.id}'
        if ref:
            detail += f'  ·  {s.distance_km(*ref):.0f} km'
        item.setLabel2(detail)
        items.append(item)
    idx = dialog.select(kodi.localize(S_SELECT, 'Select station'), items, useDetails=True)
    return stations[idx] if idx >= 0 else None


def _write(slot: int, role: str, station: Station | None) -> None:
    """Store ``station`` in the settings of ``role`` in ``slot``, or clear
    them when ``station`` is None."""
    id_key, name_key, lat_key, lon_key = config.ROLE_KEYS[role]
    k = lambda name: config.key(slot, name)
    kodi.set_setting(k(id_key), station.id if station else '')
    kodi.set_setting(k(name_key), station.name if station else '')
    kodi.set_setting(k(lat_key), f'{station.lat:.4f}' if station else '')
    kodi.set_setting(k(lon_key), f'{station.lon:.4f}' if station else '')


def _back_to_settings() -> None:
    """Settings buttons close the settings dialog first (otherwise Kodi
    overwrites what we write when the dialog saves), so reopen it, and
    refresh the weather so the change shows."""
    kodi.addon().openSettings()
    xbmc.executebuiltin('Weather.Refresh')


def run(action: str, slot: int, role: str) -> None:
    """Settings button for a single station role: ``action`` is 'pick' or
    'clear'."""
    if role not in config.ROLES or not 1 <= slot <= config.SLOTS:
        log.error(f'invalid settings action: {action} {slot} {role}')
        return
    try:
        if action == 'pick':
            station = _choose(slot)
            if station is not None:
                log.info(f'location {slot}: {role} station = {station.name} ({station.id})')
                _write(slot, role, station)
        elif action == 'clear':
            _write(slot, role, None)
    finally:
        _back_to_settings()


# ------------------------------------------------- observation station list

def _station_items(rows: list[config.StationRow], ref: tuple[float, float] | None) -> list[xbmcgui.ListItem]:
    """List items for the station rows: "1. name", detail "id … · N km"."""
    items = []
    for i, r in enumerate(rows, start=1):
        item = xbmcgui.ListItem(f'{i}. {r.name or r.id}')
        detail = f'id {r.id}'
        lat, lon = config.parse_coord(r.lat, 90), config.parse_coord(r.lon, 180)
        if ref and lat is not None and lon is not None:
            detail += f'  ·  {haversine_km(lat, lon, *ref):.0f} km'
        item.setLabel2(detail)
        items.append(item)
    return items


def _row_menu(index: int, count: int) -> list[tuple[str, str]]:
    """Popup menu entries (action, label) for row ``index`` of ``count``.
    Moves that are impossible at the ends of the list are left out."""
    menu = []
    if index > 0:
        menu.append((MOVE_UP, kodi.localize(S_MOVE_UP, 'Move up')))
    if index < count - 1:
        menu.append((MOVE_DOWN, kodi.localize(S_MOVE_DOWN, 'Move down')))
    menu.append((REPLACE, kodi.localize(S_REPLACE, 'Replace...')))
    menu.append((REMOVE, kodi.localize(S_REMOVE, 'Remove')))
    return menu


def _pick_row(slot: int, rows: list[config.StationRow], replacing: int | None = None) -> config.StationRow | None:
    """Run the station picker for a new row. A station that is already in
    the list (other than the row being replaced) is refused with a message,
    since listing it twice could never fill a gap."""
    station = _choose(slot)
    if station is None:
        return None
    if any(r.id == station.id for i, r in enumerate(rows) if i != replacing):
        xbmcgui.Dialog().ok('SMHI', kodi.localize(S_DUPLICATE, 'That station is already in the list.'))
        return None
    return config.StationRow(station.id, station.name, f'{station.lat:.4f}', f'{station.lon:.4f}')


def _edit_row(slot: int, rows: list[config.StationRow], index: int) -> int:
    """Show the popup menu for row ``index`` and apply the chosen action to
    ``rows`` in place. Returns the list position to focus next."""
    menu = _row_menu(index, len(rows))
    choice = xbmcgui.Dialog().contextmenu([label for _, label in menu])
    if choice < 0:
        return index
    action = menu[choice][0]
    if action in (MOVE_UP, MOVE_DOWN):
        # focus follows the moved station, so repeated moves are quick
        other = index - 1 if action == MOVE_UP else index + 1
        rows[index], rows[other] = rows[other], rows[index]
        return other
    if action == REPLACE:
        row = _pick_row(slot, rows, replacing=index)
        if row is not None:
            rows[index] = row
        return index
    del rows[index]
    return min(index, len(rows))


def edit_stations(slot: int) -> None:
    """Settings button: edit the observation station list of ``slot``."""
    # Kodi's settings dialog cannot show per-row menus, so the list is edited
    # with the skin's own select dialog and context menu instead: the list
    # shows the stations in priority order plus "Add station...", picking a
    # station opens its popup menu, and the list reappears after every action
    # until the user backs out. Each change is saved right away (rows kept
    # dense, summary updated), so backing out never loses anything.
    if not 1 <= slot <= config.SLOTS:
        log.error(f'invalid station list slot: {slot}')
        return
    dialog = xbmcgui.Dialog()
    rows = config.read_station_rows(kodi.get_setting, slot)
    focus = 0
    try:
        while True:
            # list: stations, then "Add" while there is room
            items = _station_items(rows, _reference_point(slot))
            if len(rows) < config.STATIONS:
                items.append(xbmcgui.ListItem('+ ' + kodi.localize(S_ADD, 'Add station...')))
            heading = kodi.localize(S_STATIONS, 'Observation stations')
            idx = dialog.select(heading, items, preselect=min(focus, len(items) - 1), useDetails=True)
            if idx < 0:
                break

            before = list(rows)
            if idx == len(rows):
                row = _pick_row(slot, rows)
                if row is not None:
                    rows.append(row)
                focus = len(rows) - 1 if row is not None else idx
            else:
                focus = _edit_row(slot, rows, idx)
            if rows == before:
                continue

            # save, and name an unnamed location after its first station
            config.write_station_rows(kodi.set_setting, slot, rows)
            log.info(f'location {slot}: stations = {[r.id for r in rows]}')
            name_key = config.key(slot, 'name')
            if rows and not kodi.get_setting(name_key):
                kodi.set_setting(name_key, rows[0].name or rows[0].id)
    finally:
        _back_to_settings()
