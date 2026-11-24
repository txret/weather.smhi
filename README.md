# weather.smhi — SMHI weather for Kodi

A Kodi weather add-on that combines two kinds of SMHI open data:

* **Current conditions** come from up to five real **observation stations**
  that you choose (temperature, humidity, wind, pressure, visibility,
  precipitation, cloud cover, gusts and dew point). Each value is taken from
  the first station in your list that reports it, so stations 2–5 fill in
  whatever your main station doesn't measure.
* **The forecast** comes from SMHI's **point forecast**: hourly for about 2.5
  days, then in 3, 6 and 12-hour steps out to 10 days. SMHI calculates
  forecasts for coordinates, not for stations. You can use your first station's
  position, another station's position, or your own latitude/longitude.

Supports up to five locations. Requires **Kodi 21 (Omega) or newer**.

## Installation

1. Build the zip (or download a release):
   ```sh
   tools/build_zip.sh            # -> weather.smhi-1.0.0.zip
   ```
2. In Kodi go to *Settings → Add-ons → Install from zip file* and pick the zip.
   You may need to enable *Unknown sources* in *Settings → System → Add-ons*
   first. Kodi installs the `script.module.requests` dependency automatically.
3. Go to *Settings → Services → Weather*, set *Service for weather
   information* to **SMHI**, then open **Settings** under it.

## Configuration

Each of the five *Location* tabs works on its own. Kodi lists only the tabs
you have filled in, numbered in order.

### Current weather

| Setting                          | What it does                                                                                                                   |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Display name**                 | The name Kodi shows. Filled in from the first station's name when you add a station to an unnamed location.                    |
| **Observation stations**         | Read-only: the stations for current conditions, in priority order.                                                             |
| **Edit observation stations…**   | Opens the station list (see below).                                                                                            |

The station list shows up to five stations, numbered in priority order, and
**Add station…** while there is room. Selecting a station opens a menu:

| Menu entry               | What it does                                                                                                                       |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| **Move up / Move down**  | Changes the station's priority.                                                                                                    |
| **Replace…**             | Picks another station for the same position.                                                                                       |
| **Remove**               | Removes the station; the ones below move up.                                                                                       |

Adding or replacing a station opens a search box (leave it empty to list every
station), then a list of the SMHI stations that are active right now, sorted
by distance once a position is known. Changes are saved straight away; press
Back to return to the settings.

The station list is downloaded once and then cached for 7 days in the add-on's
profile folder.

### Forecast

| Forecast point                           | Uses                                                        |
|------------------------------------------|-------------------------------------------------------------|
| *First station's position* (default)     | the coordinates of the first station in the list above      |
| *Another station's position*             | a second station you pick with **Choose forecast station…** |
| *Custom coordinates*                     | **Latitude** / **Longitude** in decimal degrees (WGS84)     |

A location needs at least a station *or* custom coordinates.

### Example: central Stockholm

Stockholm-Observatoriekullen (98230) is in the city centre, but it doesn't
measure wind, visibility or gusts. Stockholm-Bromma Flygplats (97200), about
7 km away, does:

* Observation stations: 1. **Stockholm-Observatoriekullen A**,
  2. **Stockholm-Bromma Flygplats**
* Forecast point: *First station's position*

How each value is chosen: **station 1 → station 2 → … → station 5 → the
forecast for the current hour**, skipping stations that currently report
nothing. So the temperature comes from Observatoriekullen,
wind and visibility from Bromma, and anything neither station reports, such as
cloud cover, from the forecast.

## What is shown

Kodi's own weather screen (and Estuary) uses the **core** properties. Kodi
converts their units and localises them itself. Most skins also read the
**extended** properties, which the add-on formats according to Kodi's region
settings (*Settings → Interface → Regional*).

### Window properties (for skinners)

All properties are set on the weather window: `Window(Weather).Property(...)`.

**Core** (raw values: °C, km/h, English text):

| Property                                                                                  | Notes                                                |
|-------------------------------------------------------------------------------------------|------------------------------------------------------|
| `Locations`, `Location1`…`Location5`                                                      | number of configured locations and their names       |
| `Current.Location`, `Current.Condition`                                                   |                                                      |
| `Current.Temperature`, `Current.FeelsLike`, `Current.DewPoint`                            | °C, whole numbers                                    |
| `Current.Wind`                                                                            | km/h; `Current.WindDirection` is `N`…`NNW` or `CALM` |
| `Current.Humidity`                                                                        | % (a number only)                                    |
| `Current.OutlookIcon`, `Current.FanartCode`                                               | Kodi weather icon code, e.g. `26.png` / `26`         |
| `Day0`…`Day6`.`Title` / `HighTemp` / `LowTemp` / `Outlook` / `OutlookIcon` / `FanartCode` | Day0 is today                                        |

**Extended** (formatted, with units):

| Property                                                                                                                                                                                                                                                      | Notes                                                                                       |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `Current.Precipitation`                                                                                                                                                                                                                                       | mm/h                                                                                        |
| `Current.Pressure`                                                                                                                                                                                                                                            | hPa                                                                                         |
| `Current.Visibility`                                                                                                                                                                                                                                          | km                                                                                          |
| `Current.Cloudiness`                                                                                                                                                                                                                                          | %                                                                                           |
| `Current.WindGust`                                                                                                                                                                                                                                            |                                                                                             |
| `Today.Sunrise`, `Today.Sunset`                                                                                                                                                                                                                               | today's sun times; empty during midnight sun / polar night                                  |
| `Today.Moonphase`                                                                                                                                                                                                                                             | e.g. *Waxing gibbous* (8 phases, localised)                                                 |
| `Current.ObservationTime`, `Current.Station`                                                                                                                                                                                                                  | when and where the observation was made                                                     |
| `Current.SymbolCode`                                                                                                                                                                                                                                          | SMHI symbol 1–27, for skins that ship SMHI's own icons                                      |
| `Hourly.1`…`Hourly.48`.`Time` / `ShortDate` / `LongDate` / `Outlook` / `OutlookIcon` / `FanartCode` / `SymbolCode` / `Temperature` / `FeelsLike` / `DewPoint` / `Humidity` / `Precipitation` / `WindSpeed` / `WindDirection` / `WindDegree` / `Pressure`      | only hourly forecast steps (about the next 48 h); precipitation is the amount for that hour |
| `Daily.1`…`Daily.10`.`ShortDay` / `LongDay` / `ShortDate` / `LongDate` / `Outlook` / `OutlookIcon` / `FanartCode` / `SymbolCode` / `HighTemperature` / `LowTemperature` / `WindSpeed` / `WindDirection` / `Precipitation` / `Humidity` / `Sunrise` / `Sunset` | Daily.1 is today; precipitation is the day's total and wind is the day's maximum            |
| `Current.IsFetched`, `Today.IsFetched`, `Hourly.IsFetched`, `Daily.IsFetched`                                                                                                                                                                                 | `true` when filled                                                                          |
| `Forecast.City`, `Forecast.Updated`, `WeatherProvider`                                                                                                                                                                                                        |                                                                                             |

Properties without data are cleared rather than left with stale values. For
example, SMHI has no UV index, so `Current.UVIndex` is always empty.

## Limitations

* The weather **symbol / condition for "now"** comes from the forecast for the
  current hour, because stations don't report a symbol. So it can disagree with
  what the station is measuring at that moment, for example rain in the
  forecast while the station has recorded no precipitation yet.
* **Daily** high/low temperatures are taken from the forecast steps. From
  about day 4 there are only a few steps per day, so the real extremes can be
  missed.
* The forecast covers Sweden and the surrounding Nordic/Baltic area. Points
  outside it log *"outside SMHI's forecast area"* and produce no forecast.
* Station observations older than 2 hours are ignored.

## Data sources and licence

Weather data: [SMHI Open Data](https://opendata.smhi.se), licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source: SMHI.
This add-on is not affiliated with SMHI.

| Data                 | Endpoint                                                                                                                   |
|----------------------|----------------------------------------------------------------------------------------------------------------------------|
| Forecast (snow1g v1) | `https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json`      |
| Observations         | `https://opendata-download-metobs.smhi.se/api/version/latest/parameter/{param}/station/{id}/period/latest-hour/data.json`  |
| Station list         | `https://opendata-download-metobs.smhi.se/api/version/latest/parameter/{1,4}/station-set/all/period/latest-hour/data.json` |

Observation parameters used:

| Parameter | Value                   |
|-----------|-------------------------|
| 1         | air temperature         |
| 3         | wind direction          |
| 4         | wind speed              |
| 6         | humidity                |
| 9         | sea-level pressure      |
| 12        | visibility              |
| 14        | 15-minute precipitation |
| 16        | total cloud cover       |
| 21        | gust                    |
| 39        | dew point               |

The code is [MIT-licensed](LICENSE). The bundled `resources/lib/astral`
is the Astral library (Apache 2.0) and is used for sunrise, sunset and the
day/night icons.

## Development

```
default.py                  entry point (Kodi runs it with the location index)
resources/settings.xml      generated by tools/gen_settings.py, do not edit
resources/lib/smhi/
  main.py         argument dispatch: weather fetch / settings buttons
  provider.py     fetch one location: forecast + stations -> properties
  forecast.py     snow1g client
  observations.py metobs client, station list + cache
  model.py        WxObs data model, derived values (feels-like, text, night)
  daily.py        per-day aggregation
  props.py        builds the window properties (pure, no Kodi imports)
  symbols.py      SMHI symbols, Kodi icon codes, precipitation types
  config.py       location slots from settings
  kodi.py         Kodi glue: window, settings, unit formatting
  settings_ui.py  station picker dialogs
tests/            pytest suite; stubs/ fakes the xbmc* modules, fixtures/ holds recorded SMHI responses
tools/            gen_settings.py, run_local.py, build_zip.sh
dev/symbol_rules/ research: how SMHI assigns its weather symbols (scripts + data)
```

```sh
python3 -m venv .venv && .venv/bin/pip install pytest requests
.venv/bin/pytest -q                                   # offline unit tests

# live fetch without Kodi, prints every window property
.venv/bin/python tools/run_local.py --station 98230 --station 97200   # in priority order
.venv/bin/python tools/run_local.py --lat 67.85 --lon 20.23 --name Kiruna --tempunit °F
.venv/bin/python tools/run_local.py --stations        # ids of active stations

python3 tools/gen_settings.py                         # after changing the settings layout
```

Settings labels live in
`resources/language/resource.language.en_gb/strings.po`. To translate the
add-on, add e.g. `resource.language.sv_se/strings.po` with the same `msgctxt` ids.

In Kodi, the add-on logs to `kodi.log` with the prefix `[weather.smhi]`. Turn
on Kodi's debug logging to see per-request details.
