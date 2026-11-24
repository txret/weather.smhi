"""Entry point, settings and Kodi glue, against the stub xbmc modules."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import pytest

from conftest import NOW, ROOT
from smhi import config, kodi, props, provider
import default


def _configure(settings, slot, **values):
    for k, v in values.items():
        settings[config.key(slot, k)] = v


STHLM = dict(name='Stockholm', station1_id='98230', station1_name='Stockholm-Observatoriekullen A',
             station1_lat='59.3417', station1_lon='18.0549', station2_id='97200')


def test_slot_mapping_skips_empty(kodi_env):
    _configure(kodi_env, 2, **STHLM)
    _configure(kodi_env, 4, fc_source='2', lat='67,85', lon='20.23')   # comma decimal ok
    slots = config.configured_slots(kodi_env.get)
    assert [s.index for s in slots] == [2, 4]
    assert slots[1].name == 'Location 4'
    assert slots[1].forecast_lat == 67.85 and slots[1].station_ids == [None] * config.STATIONS
    assert not slots[1].has_stations
    _, slot = provider.location_for_index(kodi_env.get, 2)
    assert slot.index == 4
    assert provider.location_for_index(kodi_env.get, 3)[1] is None


def test_invalid_custom_coordinates(kodi_env):
    _configure(kodi_env, 1, fc_source='2', lat='abc', lon='18')
    assert config.configured_slots(kodi_env.get) == []
    _configure(kodi_env, 1, station1_id='98230')
    (s,) = config.configured_slots(kodi_env.get)
    assert not s.has_forecast_point


def test_weather_fetch_end_to_end(kodi_env, fake_http, monkeypatch):
    import xbmcgui
    _configure(kodi_env, 1, **STHLM)
    monkeypatch.setattr(provider, 'datetime', _FrozenDatetime)
    default.main(['default.py', '1'])
    win = xbmcgui.Window(kodi.WEATHER_WINDOW)
    assert win.getProperty('Locations') == '1'
    assert win.getProperty('Location1') == 'Stockholm'
    assert win.getProperty('Current.Temperature') == '5'
    assert win.getProperty('Current.Wind') == '11'          # Bromma 3.0 m/s
    assert win.getProperty('Day6.Title')
    assert win.getProperty('Hourly.1.Time')

    # stale properties from an earlier run must be cleared
    win.setProperty('Current.UVIndex', 'old')
    win.setProperty('Daily.10.Outlook', 'old')
    del kodi_env['loc1_station2_id']
    default.main(['default.py', '1'])
    assert win.getProperty('Current.UVIndex') == ''
    assert win.getProperty('Daily.10.Outlook') != 'old'
    # without the second station, wind comes from the forecast (4.2 m/s)
    assert win.getProperty('Current.Wind') == '15'


def test_station_rows_with_gaps(kodi_env, fake_http, monkeypatch):
    """Empty station rows are skipped: the first non-empty row acts as the
    main station and later rows still fill its gaps in order."""
    import xbmcgui
    _configure(kodi_env, 1, station2_id='98230', station2_name='Stockholm-Observatoriekullen A',
               station2_lat='59.3417', station2_lon='18.0549', station4_id='97200')
    (slot,) = config.configured_slots(kodi_env.get)
    assert slot.station_ids == [None, '98230', None, '97200', None]
    assert slot.name == 'Stockholm-Observatoriekullen A'
    assert (slot.forecast_lat, slot.forecast_lon) == (59.3417, 18.0549)
    assert config.station_position(kodi_env.get, 1) == (59.3417, 18.0549)

    monkeypatch.setattr(provider, 'datetime', _FrozenDatetime)
    default.main(['default.py', '1'])
    win = xbmcgui.Window(kodi.WEATHER_WINDOW)
    assert win.getProperty('Current.Temperature') == '5'    # Observatoriekullen
    assert win.getProperty('Current.Wind') == '11'          # Bromma 3.0 m/s


def test_failed_fetch_keeps_old_props(kodi_env, monkeypatch):
    import xbmcgui
    from smhi import http
    monkeypatch.setattr(http, 'get_json', lambda url, timeout=None: (None, None))
    _configure(kodi_env, 1, **STHLM)
    win = xbmcgui.Window(kodi.WEATHER_WINDOW)
    win.setProperty('Current.Temperature', '3')
    default.main(['default.py', '1'])
    assert win.getProperty('Current.Temperature') == '3'
    assert win.getProperty('Location1') == 'Stockholm'


def test_bad_args_do_not_raise(kodi_env):
    import xbmcaddon
    default.main(['default.py'])
    default.main(['default.py', 'nonsense'])
    default.main(['default.py', 'pick', '9', 'forecast'])
    default.main(['default.py', 'pick', '1', 'station1'])   # stations use the list editor
    default.main(['default.py', 'pick', '1', 'fallback'])
    default.main(['default.py', 'stations', '9'])
    default.main(['default.py', 'stations', '0'])
    assert xbmcaddon.opened_settings == []                   # all refused up front
    assert not kodi_env


def test_pick_forecast_station(kodi_env, fake_http):
    import xbmcaddon
    import xbmcgui
    xbmcgui.Dialog.input_answer = 'bromma'
    xbmcgui.Dialog.select_answer = 0
    default.main(['default.py', 'pick', '3', 'forecast'])
    assert kodi_env['loc3_fc_id'] == '97200'
    assert kodi_env['loc3_fc_name'] == 'Stockholm-Bromma Flygplats'
    assert kodi_env['loc3_fc_lat']
    assert xbmcaddon.opened_settings     # settings reopened afterwards

    default.main(['default.py', 'clear', '3', 'forecast'])
    assert kodi_env['loc3_fc_id'] == ''
    assert kodi_env['loc3_fc_lat'] == ''


OBS = config.StationRow('98230', 'Stockholm-Observatoriekullen A', '59.3417', '18.0549')
BROMMA = config.StationRow('97200', 'Stockholm-Bromma Flygplats', '59.3537', '17.9513')


def test_station_rows_round_trip(kodi_env):
    _configure(kodi_env, 1, station2_id='98230', station2_name=OBS.name,
               station2_lat=OBS.lat, station2_lon=OBS.lon, station4_id='97200')
    assert config.read_station_rows(kodi_env.get, 1) == [OBS, config.StationRow('97200')]

    config.write_station_rows(kodi_env.__setitem__, 1, [BROMMA, OBS])
    assert config.read_station_rows(kodi_env.get, 1) == [BROMMA, OBS]
    assert kodi_env['loc1_station4_id'] == ''               # old row 4 cleared
    assert kodi_env['loc1_stations_summary'] == 'Stockholm-Bromma Flygplats, Stockholm-Observatoriekullen A'
    with pytest.raises(ValueError):
        config.write_station_rows(kodi_env.__setitem__, 1, [BROMMA] * (config.STATIONS + 1))


def _editor_lists():
    """Labels of each station list the editor showed (not the picker's)."""
    import xbmcgui
    return [labels for heading, labels, _ in xbmcgui.Dialog.selects if heading == 'Observation stations']


def test_edit_stations_add_move_remove(kodi_env, fake_http):
    import xbmcaddon
    import xbmcgui
    d = xbmcgui.Dialog
    d.input_answers = ['97200', '98230']    # picker searches, by station id
    d.select_answers = [0, 0,               # Add -> Bromma
                        1, 0,               # Add -> Observatoriekullen
                        1,                  # row 2 (Observatoriekullen) -> Move up
                        0]                  # row 1 (Observatoriekullen) -> Remove
    d.context_answers = [0, 2]
    default.main(['default.py', 'stations', '1'])

    lists = _editor_lists()
    assert lists[0] == ['+ Add station...']
    assert lists[3] == ['1. Stockholm-Observatoriekullen A', '2. Stockholm-Bromma Flygplats', '+ Add station...']
    assert d.menus == [['Move up', 'Replace...', 'Remove'], ['Move down', 'Replace...', 'Remove']]
    assert config.read_station_rows(kodi_env.get, 1) == [BROMMA]
    assert kodi_env['loc1_station2_id'] == ''
    assert kodi_env['loc1_stations_summary'] == 'Stockholm-Bromma Flygplats'
    assert kodi_env['loc1_name'] == 'Stockholm-Bromma Flygplats'   # named after the first station added
    assert xbmcaddon.opened_settings


def test_edit_stations_replace_and_duplicates(kodi_env, fake_http):
    import xbmcgui
    d = xbmcgui.Dialog
    _configure(kodi_env, 1, name='Home')
    config.write_station_rows(kodi_env.__setitem__, 1, [OBS, BROMMA])
    d.input_answers = ['97200', '97200', '97280']
    d.select_answers = [0, 0,               # row 1 -> Replace with Bromma: already listed
                        2, 0,               # Add Bromma: already listed
                        0, 0]               # row 1 -> Replace with Adelsö
    d.context_answers = [1, 1]
    default.main(['default.py', 'stations', '1'])

    assert d.oks == ['That station is already in the list.'] * 2
    rows = config.read_station_rows(kodi_env.get, 1)
    assert [r.id for r in rows] == ['97280', '97200']
    assert kodi_env['loc1_stations_summary'] == 'Adelsö A, Stockholm-Bromma Flygplats'
    assert kodi_env['loc1_name'] == 'Home'


def test_edit_stations_full_list(kodi_env, fake_http):
    import xbmcgui
    d = xbmcgui.Dialog
    rows = [config.StationRow(sid, f'S{sid}') for sid in ('98230', '97200', '97280', '9013', '188790')]
    config.write_station_rows(kodi_env.__setitem__, 1, rows)
    del kodi_env['loc1_stations_summary']
    d.select_answers = [2]                  # middle row, then cancel its menu
    default.main(['default.py', 'stations', '1'])

    assert '+ Add station...' not in _editor_lists()[0]
    assert d.menus == [['Move up', 'Move down', 'Replace...', 'Remove']]
    assert 'loc1_stations_summary' not in kodi_env          # nothing changed, nothing written
    assert config.read_station_rows(kodi_env.get, 1) == rows


def test_station_list_details():
    from smhi import settings_ui
    items = settings_ui._station_items([BROMMA, config.StationRow('1')], (59.3417, 18.0549))
    assert [i.label for i in items] == ['1. Stockholm-Bromma Flygplats', '2. 1']
    assert re.fullmatch(r'id 97200  ·  \d+ km', items[0].label2)
    assert items[1].label2 == 'id 1'                        # no position, no distance


def test_kodi_formatter_units(monkeypatch):
    import xbmc
    monkeypatch.setitem(xbmc.REGION, 'tempunit', '°F')
    monkeypatch.setitem(xbmc.REGION, 'speedunit', 'kts')
    f = kodi.KodiFormatter()
    assert f.temp(0) == '32°F'
    assert f.speed(10) == '19 kts'
    monkeypatch.setitem(xbmc.REGION, 'speedunit', 'Beaufort')
    assert kodi.KodiFormatter().speed(10) == '5 Beaufort'
    monkeypatch.setitem(xbmc.REGION, 'speedunit', 'bogus')
    assert kodi.KodiFormatter().speed(10) == '36 km/h'


def test_settings_xml_matches_generator_and_strings():
    from tools import gen_settings
    with open(f'{ROOT}/resources/settings.xml', encoding='utf-8') as f:
        assert f.read() == gen_settings.generate(), 'run tools/gen_settings.py'
    tree = ET.parse(f'{ROOT}/resources/settings.xml')
    with open(f'{ROOT}/resources/language/resource.language.en_gb/strings.po', encoding='utf-8') as f:
        ids = set(re.findall(r'msgctxt "#(\d+)"', f.read()))
    used = set()
    for el in tree.iter():
        for attr in ('label', 'help'):
            if el.get(attr):
                used.add(el.get(attr))
        if el.tag == 'heading':
            used.add(el.text)
    assert used <= ids, used - ids
    # every symbol string exists too
    assert {str(32100 + i) for i in range(1, 28)} <= ids


def test_versions_match():
    import smhi
    root = ET.parse(f'{ROOT}/addon.xml').getroot()
    assert root.get('version') == smhi.__version__
    assert root.get('id') == smhi.ADDON_ID


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)
