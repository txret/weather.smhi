from datetime import date

from conftest import NOW, STOCKHOLM, load_fixture
from smhi import daily, forecast, props
from smhi.model import WxObs


def _steps():
    return forecast.parse(load_fixture('snow1g_stockholm.json'))


def test_daily_summary():
    days = daily.summarize(_steps(), NOW, STOCKHOLM)
    assert days[0].date == date(2026, 11, 9)
    assert 9 <= len(days) <= 10
    assert all(d.high >= d.low for d in days)
    assert all(a.date < b.date for a, b in zip(days, days[1:]))
    # day 2 has hourly data: noon representative
    rep = days[1].representative.time.astimezone(STOCKHOLM)
    assert rep.hour in (11, 12, 13)


def test_build_props_types_and_core_values():
    steps = _steps()
    days = daily.summarize(steps, NOW, STOCKHOLM)
    current = WxObs(time=NOW, lat=59.34, lon=18.05, temperature=4.8, wind_speed=3.0,
                    wind_degree=220, humidity=76, symbol=steps[0].symbol, source='Station X')
    p = props.build('Stockholm', current, steps, days, props.Formatter(STOCKHOLM), NOW)

    assert all(isinstance(v, str) and v for v in p.values())
    assert set(p) <= set(props.all_keys())
    # core values are raw metric numbers and English text, Kodi formats them
    assert p['Current.Temperature'] == '5'
    assert p['Current.Wind'] == '11'
    assert p['Current.WindDirection'] == 'SW'
    assert p['Current.Humidity'] == '76'
    assert p['Current.Condition'] == 'Overcast'
    assert p['Current.OutlookIcon'] == '26.png'
    assert p['Current.Station'] == 'Station X'
    assert p['Day0.Title'] == 'Monday'
    for i in range(7):
        assert float(p[f'Day{i}.HighTemp']) >= float(p[f'Day{i}.LowTemp'])
        assert p[f'Day{i}.OutlookIcon'].endswith('.png')
    # extended
    assert p['Hourly.1.Time'] == '14:00'          # 13:00Z in Stockholm
    assert p['Hourly.1.Temperature'].endswith('°C')
    assert 'Hourly.49.Time' not in p
    assert p['Daily.1.LongDay'] == 'Monday'
    assert p['Hourly.IsFetched'] == p['Daily.IsFetched'] == p['Current.IsFetched'] == 'true'
    assert 'Current.UVIndex' not in p


def test_build_with_nothing():
    p = props.build('X', None, None, None, now=NOW)
    assert 'Current.IsFetched' not in p and p['WeatherProvider'] == 'SMHI'


def test_calm_wind():
    p = props.build('X', WxObs(wind_speed=0.2, wind_degree=10), None, None, now=NOW)
    assert p['Current.WindDirection'] == 'CALM'


def test_skin_contract_sun_times_and_hourly_dates():
    """Skins read Today.Sunrise/Sunset, and match Hourly.N.LongDate against
    Daily.N.LongDate to show each day's hours, so the two must agree exactly."""
    steps = _steps()
    days = daily.summarize(steps, NOW, STOCKHOLM)
    current = WxObs(time=NOW, lat=59.34, lon=18.05, temperature=4.8, symbol=steps[0].symbol)
    p = props.build('Stockholm', current, steps, days, props.Formatter(STOCKHOLM), NOW)

    assert p['Today.Sunrise'] and p['Today.Sunset']
    assert 'Current.Sunrise' not in p and 'Current.Sunset' not in p
    assert {'Today.Sunrise', 'Today.Sunset'} <= set(props.all_keys())

    daily_dates = [p[f'Daily.{i}.LongDate'] for i in range(1, 11) if f'Daily.{i}.LongDate' in p]
    hourly_dates = [p[f'Hourly.{i}.LongDate'] for i in range(1, 49) if f'Hourly.{i}.LongDate' in p]
    assert hourly_dates and set(hourly_dates) <= set(daily_dates)
    assert hourly_dates[0] == daily_dates[0]


def test_today_group():
    steps = _steps()
    days = daily.summarize(steps, NOW, STOCKHOLM)
    current = WxObs(time=NOW, lat=59.34, lon=18.05, temperature=4.8)
    p = props.build('Stockholm', current, steps, days, props.Formatter(STOCKHOLM), NOW)
    assert p['Today.IsFetched'] == 'true'
    assert p['Today.Sunrise'] < p['Today.Sunset']          # 'HH:MM' strings
    assert p['Today.Moonphase'] in props.MOON_PHASES
    assert 'Current.Sunrise' not in p and 'Current.Sunset' not in p
    # Daily.1 is today, so its sun times match Today.*
    assert (p['Daily.1.Sunrise'], p['Daily.1.Sunset']) == (p['Today.Sunrise'], p['Today.Sunset'])
    assert p['Daily.10.Sunrise'] > p['Daily.1.Sunrise']    # mornings get later in November


def test_moon_phase_known_dates():
    from smhi.model import moon_phase, MOON_PHASES
    assert MOON_PHASES[moon_phase(date(2024, 1, 11))] == 'New moon'
    assert MOON_PHASES[moon_phase(date(2024, 1, 25))] == 'Full moon'


def test_today_polar_night_has_no_sun_times():
    from datetime import datetime, timezone
    now = datetime(2026, 12, 21, 11, tzinfo=timezone.utc)
    p = props.build('Kiruna', WxObs(time=now, lat=67.85, lon=20.23), None, None,
                    props.Formatter(STOCKHOLM), now)
    assert p['Today.IsFetched'] == 'true'
    assert 'Today.Sunrise' not in p and 'Today.Moonphase' in p
