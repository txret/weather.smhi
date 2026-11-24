from datetime import datetime, timezone

import pytest

from smhi.model import WxObs, merge
from smhi.symbols import Precip, Wsymb2, fanart_code, precip_from_ptype, TEXT


def test_empty_obs_never_raises():
    o = WxObs()
    for attr in ('feels_like', 'wind_direction', 'cloud_text', 'precip_text',
                 'effective_symbol', 'condition_text', 'night'):
        getattr(o, attr)
    assert o.sun_times() == (None, None)


def test_wind_chill_uses_kmh():
    o = WxObs(temperature=0.0, wind_speed=10.0)   # 36 km/h
    assert o.feels_like == pytest.approx(-7.05, abs=0.1)  # standard table: about -7
    assert WxObs(temperature=0.0).feels_like == 0.0


def test_heat_index():
    assert WxObs(temperature=32, humidity=70).feels_like > 32


def test_wind_direction():
    assert WxObs(wind_degree=0).wind_direction == 'N'
    assert WxObs(wind_degree=225).wind_direction == 'SW'
    assert WxObs(wind_degree=355).wind_direction == 'N'


def test_precip_text_no_rounding():
    assert WxObs(precip_intensity=0.3, precip_type=Precip.DRIZZLE).precip_text == 'moderate drizzle'
    assert WxObs(precip_intensity=0.3, temperature=5).precip_text == 'light rain'
    assert WxObs(precip_intensity=0.05).precip_text is None


def test_forecast_symbol_wins_over_derived():
    assert WxObs(symbol=Wsymb2.FOG, cloud_cover=0).effective_symbol == Wsymb2.FOG


@pytest.mark.parametrize('octas, expected', [
    (0, 1), (1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (7, 4), (8, 6)])
def test_derived_cloud_class(octas, expected):
    # SMHI's mapping from total cloud; CLOUDY (5) is never used
    assert WxObs(cloud_cover=octas).effective_symbol == Wsymb2(expected)


def test_derived_symbol_needs_data():
    assert WxObs().effective_symbol is None
    assert WxObs(cloud_cover=12).effective_symbol is None
    assert WxObs(precip_intensity=0.05).effective_symbol is None   # dry, nothing else known


def test_derived_fog():
    assert WxObs(visibility=0.9, cloud_cover=0).effective_symbol == Wsymb2.FOG
    assert WxObs(visibility=1.0, cloud_cover=0).effective_symbol == Wsymb2.CLEAR
    # precipitation takes precedence over fog
    assert WxObs(visibility=0.5, precip_intensity=0.2, temperature=5).effective_symbol == Wsymb2.LIGHT_RAIN_SHOWERS


@pytest.mark.parametrize('rate, expected', [
    (0.09, Wsymb2.OVERCAST),             # below 0.1 mm/h is dry
    (0.1, Wsymb2.LIGHT_RAIN),
    (0.49, Wsymb2.LIGHT_RAIN),
    (0.5, Wsymb2.MODERATE_RAIN),
    (7.5, Wsymb2.MODERATE_RAIN),
    (7.6, Wsymb2.HEAVY_RAIN),
])
def test_derived_rain_intensity(rate, expected):
    assert WxObs(precip_intensity=rate, precip_type=Precip.RAIN, cloud_cover=8).effective_symbol == expected


@pytest.mark.parametrize('rate, expected', [
    (0.4, Wsymb2.LIGHT_SNOWFALL), (0.5, Wsymb2.MODERATE_SNOWFALL), (2.5, Wsymb2.HEAVY_SNOWFALL)])
def test_derived_snow_intensity(rate, expected):
    # moderate starts at 0.5 mm/h for every kind of precipitation
    assert WxObs(precip_intensity=rate, precip_type=Precip.SNOW, cloud_cover=8).effective_symbol == expected


@pytest.mark.parametrize('cloud, expected', [
    (7, Wsymb2.LIGHT_SLEET_SHOWERS), (8, Wsymb2.LIGHT_SLEET), (None, Wsymb2.LIGHT_SLEET_SHOWERS)])
def test_derived_showers_unless_overcast(cloud, expected):
    assert WxObs(precip_intensity=0.2, precip_type=Precip.SLEET, cloud_cover=cloud).effective_symbol == expected


@pytest.mark.parametrize('ptype, temperature, expected', [
    (Precip.DRIZZLE, None, Wsymb2.LIGHT_RAIN),
    (Precip.FREEZING_RAIN, None, Wsymb2.LIGHT_RAIN),
    (Precip.FREEZING_DRIZZLE, None, Wsymb2.LIGHT_RAIN),
    (None, -5, Wsymb2.LIGHT_SNOWFALL),      # type from temperature
    (None, 0, Wsymb2.LIGHT_SLEET),
    (Precip.NONE, 5, Wsymb2.LIGHT_RAIN),
    (None, None, Wsymb2.LIGHT_RAIN),        # nothing known: rain
])
def test_derived_precip_kind(ptype, temperature, expected):
    o = WxObs(precip_intensity=0.2, precip_type=ptype, temperature=temperature, cloud_cover=8)
    assert o.effective_symbol == expected


def test_derived_thunder():
    rain = dict(precip_intensity=0.2, precip_type=Precip.RAIN)
    assert WxObs(thunder_prob=50, cloud_cover=7, **rain).effective_symbol == Wsymb2.THUNDERSTORM
    assert WxObs(thunder_prob=50, cloud_cover=8, **rain).effective_symbol == Wsymb2.THUNDER
    assert WxObs(thunder_prob=49, cloud_cover=8, **rain).effective_symbol == Wsymb2.LIGHT_RAIN
    # thunder never replaces snow, and needs precipitation
    snow = WxObs(thunder_prob=80, cloud_cover=8, precip_intensity=0.2, precip_type=Precip.SNOW)
    assert snow.effective_symbol == Wsymb2.LIGHT_SNOWFALL
    assert WxObs(thunder_prob=80, cloud_cover=8).effective_symbol == Wsymb2.OVERCAST


@pytest.mark.parametrize('code, expected', [
    (0, Precip.NONE), (1, Precip.RAIN), (3, Precip.FREEZING_RAIN), (5, Precip.SNOW),
    (6, Precip.SLEET),                      # wet snow: SMHI shows sleet
    (7, Precip.SLEET), (8, Precip.SLEET), (11, Precip.DRIZZLE), (12, Precip.FREEZING_DRIZZLE),
    (99, None), (None, None), ('x', None)])
def test_precip_from_ptype(code, expected):
    assert precip_from_ptype(code) == expected


def test_merge_order():
    a = WxObs(temperature=1.0)
    b = WxObs(temperature=2.0, wind_speed=3.0)
    m = merge(None, a, b)
    assert (m.temperature, m.wind_speed) == (1.0, 3.0)
    assert merge(None, None) is None


@pytest.mark.parametrize('code', list(Wsymb2))
def test_every_symbol_has_text_and_icons(code):
    assert TEXT[code]
    assert fanart_code(code, False) is not None
    assert fanart_code(code, True) is not None


@pytest.mark.parametrize('when', [
    datetime(2026, 6, 21, 0, 0, tzinfo=timezone.utc),    # midnight sun
    datetime(2026, 12, 21, 11, 0, tzinfo=timezone.utc),  # polar night
])
def test_polar_kiruna_does_not_raise(when):
    o = WxObs(time=when, lat=67.85, lon=20.23)
    sunrise, sunset = o.sun_times()
    assert sunrise is None and sunset is None
    assert o.night is (when.month == 12)


def test_night_stockholm():
    assert WxObs(time=datetime(2026, 11, 9, 22, tzinfo=timezone.utc), lat=59.3, lon=18.0).night
    assert not WxObs(time=datetime(2026, 11, 9, 11, tzinfo=timezone.utc), lat=59.3, lon=18.0).night
    rise, sset = WxObs(time=datetime(2026, 11, 9, 11, tzinfo=timezone.utc), lat=59.3, lon=18.0).sun_times(timezone.utc)
    assert rise < sset
