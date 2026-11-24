from datetime import timedelta

from conftest import NOW
from smhi import forecast, observations
from smhi.model import merge


def test_single_station(fake_http):
    obs = observations.get_station_obs('98230', NOW)
    assert obs.source == 'Stockholm-Observatoriekullen A'
    assert obs.temperature == 4.8
    assert obs.humidity == 76
    assert obs.dew_point == 0.9
    assert obs.pressure == 1021.7
    assert obs.precip_intensity == 0.0
    # Observatoriekullen does not measure wind or visibility
    assert obs.wind_speed is None and obs.visibility is None
    assert abs(obs.lat - 59.3417) < 1e-6


def test_stations_fill_gaps_in_order_then_forecast(fake_http):
    first = observations.get_station_obs('98230', NOW)
    second = observations.get_station_obs('97200', NOW)
    fc = forecast.step_at(forecast.get_forecast(59.3417, 18.0549), NOW)
    cur = merge(first, second, fc)
    assert cur.temperature == 4.8          # first station wins over Bromma's 4.6
    assert cur.wind_speed == 3.0           # from Bromma
    assert cur.wind_degree == 220          # from Bromma
    assert cur.visibility == 45.0          # Bromma, metres -> km
    assert cur.cloud_cover == 8            # from forecast
    assert cur.symbol is not None          # from forecast
    assert cur.source == 'Stockholm-Observatoriekullen A'
    # stations that returned nothing are skipped
    assert merge(None, first, None, second, fc) == cur


def test_station_order_decides(fake_http):
    first = observations.get_station_obs('98230', NOW)
    second = observations.get_station_obs('97200', NOW)
    cur = merge(second, first)
    assert cur.temperature == 4.6          # Bromma first now
    assert cur.source == 'Stockholm-Bromma Flygplats'


def test_stale_values_ignored(fake_http):
    assert observations.get_station_obs('98230', NOW + timedelta(hours=5)) is None


def test_unknown_station(fake_http):
    assert observations.get_station_obs('1', NOW) is None


def test_station_list_and_cache(fake_http, tmp_path):
    stations = observations.list_stations(str(tmp_path))
    ids = {s.id for s in stations}
    assert {'98230', '97200'} <= ids
    assert (tmp_path / observations.STATION_CACHE_FILE).exists()
    n = len(fake_http)
    again = observations.list_stations(str(tmp_path))
    assert again == stations and len(fake_http) == n   # served from cache


def test_haversine():
    # Observatoriekullen -> Bromma is roughly 7 km
    d = observations.haversine_km(59.3417, 18.0549, 59.3537, 17.9513)
    assert 5 < d < 8
