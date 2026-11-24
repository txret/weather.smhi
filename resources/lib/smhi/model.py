"""Weather observation / forecast step model.

All measured fields are Optional: stations rarely report everything, and
forecast steps carry SMHI's missing-value markers. Every derived value returns
None instead of raising when its inputs are missing.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date, datetime, tzinfo

from .symbols import Precip, Wsymb2, TEXT as SYMBOL_TEXT

COMPASS = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
           'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')

# Sun elevation at sunrise/sunset (refraction + solar disc radius)
SUNRISE_ELEVATION = -0.833

# Symbol rules inferred from SMHI's own forecast symbols (dev/symbol_rules)
PRECIP_FROM = 0.1        # mm/h; SMHI: step median >= 0.1 mm
MODERATE_FROM = 0.5      # mm/h, the same for rain, sleet and snow
# Heavy precipitation never occurred in the analysed data, so these are not
# inferred from SMHI; they are the add-on's earlier values.
HEAVY_FROM = {'rain': 7.6, 'sleet': 7.6, 'snow': 2.5}   # mm/h
THUNDER_FROM = 50        # % thunderstorm probability; only replaces rain
FOG_BELOW = 1            # km visibility

# symbol per (kind, showers): light, moderate, heavy
PRECIP_SYMBOLS = {
    ('rain', True): (Wsymb2.LIGHT_RAIN_SHOWERS, Wsymb2.MODERATE_RAIN_SHOWERS, Wsymb2.HEAVY_RAIN_SHOWERS),
    ('rain', False): (Wsymb2.LIGHT_RAIN, Wsymb2.MODERATE_RAIN, Wsymb2.HEAVY_RAIN),
    ('sleet', True): (Wsymb2.LIGHT_SLEET_SHOWERS, Wsymb2.MODERATE_SLEET_SHOWERS, Wsymb2.HEAVY_SLEET_SHOWERS),
    ('sleet', False): (Wsymb2.LIGHT_SLEET, Wsymb2.MODERATE_SLEET, Wsymb2.HEAVY_SLEET),
    ('snow', True): (Wsymb2.LIGHT_SNOW_SHOWERS, Wsymb2.MODERATE_SNOW_SHOWERS, Wsymb2.HEAVY_SNOW_SHOWERS),
    ('snow', False): (Wsymb2.LIGHT_SNOWFALL, Wsymb2.MODERATE_SNOWFALL, Wsymb2.HEAVY_SNOWFALL),
}

# total cloud cover in octas (index) -> symbol; SMHI never uses CLOUDY (5)
CLOUD_SYMBOLS = (Wsymb2.CLEAR, Wsymb2.CLEAR,
                 Wsymb2.NEARLY_CLEAR, Wsymb2.NEARLY_CLEAR,
                 Wsymb2.VARIABLE_CLOUDINESS, Wsymb2.VARIABLE_CLOUDINESS,
                 Wsymb2.HALFCLEAR, Wsymb2.HALFCLEAR,
                 Wsymb2.OVERCAST)


def _precip_kind(pt: Precip | None) -> str | None:
    """Symbol family of a precipitation type: freezing rain and (freezing)
    drizzle are shown as rain, like SMHI does; None if the type is unknown."""
    if pt in (None, Precip.NONE):
        return None
    return {Precip.SNOW: 'snow', Precip.SLEET: 'sleet'}.get(pt, 'rain')


@dataclass
class WxObs:
    time: datetime | None = None          # aware; end of interval for forecast steps
    lat: float | None = None
    lon: float | None = None
    temperature: float | None = None      # °C
    dew_point: float | None = None        # °C
    humidity: int | None = None           # %
    wind_speed: float | None = None       # m/s
    wind_degree: int | None = None        # degrees, wind *from*
    wind_gust: float | None = None        # m/s
    pressure: float | None = None         # hPa, mean sea level
    visibility: float | None = None       # km
    cloud_cover: int | None = None        # octas 0–8
    precip_intensity: float | None = None  # mm/h
    precip_amount: float | None = None    # mm over the interval
    precip_type: Precip | None = None
    thunder_prob: int | None = None       # %
    symbol: Wsymb2 | None = None
    interval_hours: float | None = None   # forecast step length
    source: str | None = None             # station name / 'forecast', informational

    # ---------------------------------------------------------------- derived

    @property
    def feels_like(self) -> float | None:
        t = self.temperature
        if t is None:
            return None
        if t <= 10 and self.wind_speed is not None:
            v = self.wind_speed * 3.6  # formula is defined for km/h
            if v > 4.8:
                return (13.12 + 0.6215 * t - 11.37 * v ** 0.16
                        + 0.3965 * t * v ** 0.16)
        if t >= 27 and self.humidity is not None and self.humidity >= 40:
            rh = self.humidity
            return (-8.78469475556 + 1.61139411 * t + 2.33854883889 * rh
                    - 0.14611605 * t * rh - 0.012308094 * t ** 2
                    - 0.0164248277778 * rh ** 2 + 0.002211732 * t ** 2 * rh
                    + 0.00072546 * t * rh ** 2 - 0.000003582 * t ** 2 * rh ** 2)
        return t

    @property
    def wind_direction(self) -> str | None:
        """16-point compass abbreviation (English), e.g. 'SW'."""
        if self.wind_degree is None:
            return None
        return COMPASS[round(self.wind_degree / 22.5) % 16]

    @property
    def calm(self) -> bool:
        return self.wind_speed is not None and self.wind_speed < 0.5

    @property
    def cloud_text(self) -> str | None:
        c = self.cloud_cover
        if c is None or not 0 <= c <= 8:
            return None
        if c == 0:
            return 'clear sky'
        if c <= 2:
            return 'few clouds'
        if c <= 5:
            return 'partly cloudy'
        if c <= 7:
            return 'cloudy'
        return 'overcast'

    @property
    def precip_text(self) -> str | None:
        """Text from precipitation intensity (mm/h) and type, or None if dry."""
        p = self.precip_intensity
        if p is None or p < 0.1:
            return None
        pt = self.precip_type
        if pt in (None, Precip.NONE):
            pt = self._type_from_temperature()
        if pt is None:
            return 'precipitation'
        if pt in (Precip.DRIZZLE, Precip.FREEZING_DRIZZLE):
            grade = 'light' if p < 0.25 else 'moderate' if p < 0.5 else 'heavy'
        elif pt == Precip.SNOW:
            grade = 'light' if p < 1 else 'moderate' if p < 2.5 else 'heavy'
        else:
            grade = 'light' if p < 2.5 else 'moderate' if p < 7.6 else 'heavy'
        noun = {
            Precip.SNOW: 'snow', Precip.SLEET: 'sleet', Precip.RAIN: 'rain',
            Precip.FREEZING_RAIN: 'freezing rain', Precip.DRIZZLE: 'drizzle',
            Precip.FREEZING_DRIZZLE: 'freezing drizzle',
        }[pt]
        return f'{grade} {noun}'

    def _type_from_temperature(self) -> Precip | None:
        if self.temperature is None:
            return None
        if self.temperature < -1:
            return Precip.SNOW
        if self.temperature > 1:
            return Precip.RAIN
        return Precip.SLEET

    @property
    def effective_symbol(self) -> Wsymb2 | None:
        """The SMHI symbol, or one derived from clouds/precipitation/visibility
        when the data came from a station only."""
        if self.symbol is not None:
            return self.symbol
        return self._derive_symbol()

    def _derive_symbol(self) -> Wsymb2 | None:
        """A Wsymb2 symbol from the measured values, following the rules SMHI
        uses for its own forecast symbols, or None if there is too little data."""
        # The rules and cut-offs were inferred by comparing SMHI's snow1g
        # symbol_code with the other forecast parameters of 129 000 steps (see
        # dev/symbol_rules). Precedence follows SMHI: precipitation (thunder
        # first), then fog, then the cloud class. Stations report only total
        # cloud cover, not cloud layers, so the cloud class uses the best
        # mapping from total cloud alone (it matched SMHI on 89% of steps).
        p = self.precip_intensity
        if p is not None and p >= PRECIP_FROM:
            kind = _precip_kind(self.precip_type) or _precip_kind(self._type_from_temperature()) or 'rain'
            # SMHI: precipitation under anything but full cover is showers;
            # unknown cloud cover keeps the add-on's earlier default (showers)
            showers = self.cloud_cover is None or self.cloud_cover < 8
            if kind == 'rain' and self.thunder_prob is not None and self.thunder_prob >= THUNDER_FROM:
                return Wsymb2.THUNDERSTORM if showers else Wsymb2.THUNDER
            level = 2 if p >= HEAVY_FROM[kind] else 1 if p >= MODERATE_FROM else 0
            return PRECIP_SYMBOLS[kind, showers][level]
        if self.visibility is not None and self.visibility < FOG_BELOW:
            return Wsymb2.FOG
        c = self.cloud_cover
        if c is None or not 0 <= c <= 8:
            return None
        return CLOUD_SYMBOLS[c]

    @property
    def condition_text(self) -> str | None:
        """English condition description."""
        sym = self.effective_symbol
        if sym is not None:
            return SYMBOL_TEXT[sym]
        parts = [x for x in (self.cloud_text, self.precip_text) if x]
        return ', '.join(parts).capitalize() if parts else None

    # ------------------------------------------------------------------- sun

    def _observer(self):
        from astral import Observer
        return Observer(latitude=self.lat, longitude=self.lon)

    @property
    def night(self) -> bool:
        """True when the sun is below the horizon. Never raises, also works
        during polar day/night."""
        if self.time is None or self.lat is None or self.lon is None:
            return False
        from astral.sun import elevation
        try:
            return elevation(self._observer(), self.time) < SUNRISE_ELEVATION
        except (ValueError, ArithmeticError):
            return False

    def sun_times(self, tz: tzinfo | None = None) -> tuple[datetime | None, datetime | None]:
        """(sunrise, sunset) on the local date of ``time``."""
        if self.time is None or self.lat is None or self.lon is None:
            return None, None
        local = self.time.astimezone(tz)
        return sun_times(self.lat, self.lon, local.date(), local.tzinfo)


def sun_times(lat: float, lon: float, day: date, tz: tzinfo | None = None) -> tuple[datetime | None, datetime | None]:
    """(sunrise, sunset) on ``day``; None for each that does not happen
    (midnight sun / polar night). ``tz`` None means the system time zone."""
    from astral import Observer
    from astral.sun import sunrise, sunset
    tz = tz or datetime.now().astimezone().tzinfo
    obs = Observer(latitude=lat, longitude=lon)
    result = []
    for fn in (sunrise, sunset):
        try:
            result.append(fn(obs, day, tzinfo=tz))
        except (ValueError, ArithmeticError):
            result.append(None)
    return result[0], result[1]


MOON_PHASES = ('New moon', 'Waxing crescent', 'First quarter', 'Waxing gibbous',
               'Full moon', 'Waning gibbous', 'Last quarter', 'Waning crescent')


def moon_phase(day: date) -> int:
    """Index into MOON_PHASES (0 = new moon, 4 = full moon)."""
    from astral.moon import phase
    return int((phase(day) + 1.75) // 3.5) % 8


def merge(*sources: WxObs | None) -> WxObs | None:
    """Field-wise merge: each field comes from the first source, in argument
    order, where it is not None; None sources are skipped. ``time``/``lat``/
    ``lon``/``source`` follow the same rule, so the first source wins."""
    sources = [s for s in sources if s is not None]
    if not sources:
        return None
    values = {}
    for f in dataclasses.fields(WxObs):
        values[f.name] = next((getattr(s, f.name) for s in sources
                               if getattr(s, f.name) is not None), None)
    return WxObs(**values)
