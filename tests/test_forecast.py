from datetime import datetime, timedelta, timezone

from conftest import NOW, load_fixture
from smhi import forecast
from smhi.symbols import Precip, Wsymb2


def test_parse_fixture():
    steps = forecast.parse(load_fixture('snow1g_stockholm.json'))
    assert len(steps) == 83
    first = steps[0]
    assert first.time == datetime(2026, 11, 9, 13, tzinfo=timezone.utc)
    assert first.temperature == 5.2
    assert first.wind_degree == 238
    assert first.cloud_cover == 8
    assert first.symbol == Wsymb2.OVERCAST
    assert first.interval_hours == 1
    assert first.lat is not None and first.lon is not None
    assert all(a.time < b.time for a, b in zip(steps, steps[1:]))


def test_missing_values_become_none():
    doc = {'geometry': {'coordinates': [18.0, 59.3]}, 'timeSeries': [{
        'time': '2026-11-09T13:00:00Z',
        'intervalParametersStartTime': '2026-11-09T12:00:00Z',
        'data': {'air_temperature': 9999, 'cloud_base_altitude': 9999,
                 'precipitation_frozen_part': -9, 'symbol_code': 99,
                 'cloud_area_fraction': 9999, 'wind_speed': 3.0},
    }]}
    (s,) = forecast.parse(doc)
    assert s.temperature is None
    assert s.cloud_cover is None
    assert s.symbol is None          # unknown symbol code
    assert s.wind_speed == 3.0


def test_precip_amount_to_intensity():
    doc = {'geometry': {'coordinates': [18.0, 59.3]}, 'timeSeries': [{
        'time': '2026-11-12T12:00:00Z',
        'intervalParametersStartTime': '2026-11-12T06:00:00Z',
        'data': {'precipitation_amount_mean': 0.6,
                 'predominant_precipitation_type_at_surface': 5},
    }]}
    (s,) = forecast.parse(doc)
    assert s.interval_hours == 6
    assert s.precip_amount == 0.6
    assert abs(s.precip_intensity - 0.1) < 1e-9
    assert s.precip_type == Precip.SNOW


def test_step_at_covering_interval():
    steps = forecast.parse(load_fixture('snow1g_stockholm.json'))
    s = forecast.step_at(steps, NOW)       # 12:30 is inside 12:00..13:00
    assert s is steps[0]
    s = forecast.step_at(steps, NOW + timedelta(hours=1))
    assert s is steps[1]
    assert forecast.step_at([], NOW) is None


def test_get_forecast_404(monkeypatch):
    from smhi import http
    monkeypatch.setattr(http, 'get_json', lambda url, timeout=None: (404, None))
    assert forecast.get_forecast(40.0, 30.0) is None


def test_get_forecast_rounds_coordinates(fake_http):
    forecast.get_forecast(59.341712345, 18.054987654)
    assert fake_http[-1].endswith('/lon/18.055/lat/59.3417/data.json')
