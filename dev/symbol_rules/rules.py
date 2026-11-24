"""The inferred Wsymb2 ruleset, scored against SMHI's own symbols.

Usage: venv/bin/python rules.py data.pkl   (run from this folder)
"""
import sys

import numpy as np
import pandas as pd

from explore import INTENSITY, KIND, PRECIP_SYMBOLS, load

RAIN_PTYPES = {1, 3, 11, 12}     # rain, freezing rain, drizzle, freezing drizzle
SNOW_PTYPES = {5}
SLEET_PTYPES = {6, 7, 8}         # wet snow (seen); rain/snow mix, ice pellets (assumed)

# symbol per (kind, showers) for intensity light / moderate / heavy
PRECIP_SYMBOL = {
    ('rain', True): (8, 9, 10), ('rain', False): (18, 19, 20),
    ('sleet', True): (12, 13, 14), ('sleet', False): (22, 23, 24),
    ('snow', True): (15, 16, 17), ('snow', False): (25, 26, 27),
}

# cloud class from "effective" cloud: low/medium + HIGH_WEIGHT * high-only part
HIGH_WEIGHT = 0.75
CLOUD_CUTS = ((7.25, 6), (5.5, 4), (3.25, 3), (1.5, 2))   # (from eff octas, symbol)

MODERATE_FROM = 0.5      # median mm/h
HEAVY_FROM = np.inf      # not seen in the data


def kind_of(ptype: int) -> str:
    """Precipitation kind of an ECMWF ptype code."""
    if ptype in SNOW_PTYPES:
        return 'snow'
    if ptype in SLEET_PTYPES:
        return 'sleet'
    return 'rain'


def cloud_symbol(tcc: float, lm: float) -> int:
    """Cloud class 1-4 or 6 (5 'cloudy' is never used)."""
    eff = lm + HIGH_WEIGHT * (tcc - lm)
    return next((sym for cut, sym in CLOUD_CUTS if eff >= cut), 1)


def symbol(r) -> int:
    """Wsymb2 for one forecast step, by the inferred rules."""
    # Order of precedence found in the data: precipitation (thunder first),
    # then fog, then the cloud class.
    if r.precipitation_amount_median >= 0.1:
        kind = kind_of(r.predominant_precipitation_type_at_surface)
        showers = r.cloud_area_fraction < 8
        if kind == 'rain' and r.thunderstorm_probability >= 50:
            return 11 if showers else 21
        rate = r.precipitation_amount_median / r.hours
        level = 2 if rate >= HEAVY_FROM else 1 if rate >= MODERATE_FROM else 0
        return PRECIP_SYMBOL[kind, showers][level]
    if r.visibility_in_air < 1:
        return 7
    return cloud_symbol(r.cloud_area_fraction, r.lm_cloud)


def addon_cloud_symbol(c: float) -> int:
    """The add-on's current cloud thresholds (model.WxObs._derive_symbol)."""
    return 1 if c == 0 else 2 if c <= 2 else 3 if c <= 4 else 4 if c <= 6 else 5 if c == 7 else 6


def tcc_only_symbol(c: float) -> int:
    """Best mapping from total cloud alone (majority per octa, hourly data)."""
    return {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 6}[int(c)]


def main(path: str) -> None:
    """Score the ruleset overall, per step length and per decision."""
    df = load(path)
    df['pred'] = [symbol(r) for r in df.itertuples()]
    df['ok'] = df.pred == df.symbol_code
    print(f'overall agreement {df.ok.mean():.4f} on {len(df)} steps')
    print('by step length:', df.groupby('hours').ok.mean().round(4).to_dict())

    # per decision, hourly steps
    h = df[df.hours == 1]
    is_p = h.symbol_code.isin(PRECIP_SYMBOLS)
    pred_p = h.pred.isin(PRECIP_SYMBOLS)
    print('\nhourly decisions:')
    print(f'  precip or not   {(is_p == pred_p).mean():.4f}')
    both = h[is_p & pred_p & ~h.symbol_code.isin({11, 21}) & ~h.pred.isin({11, 21})]
    print(f'  kind            {(both.symbol_code.map(KIND) == both.pred.map(KIND)).mean():.4f}')
    print(f'  intensity       {(both.symbol_code.map(INTENSITY) == both.pred.map(INTENSITY)).mean():.4f}')
    sh = lambda s: s.isin({8, 9, 10, 11, 12, 13, 14, 15, 16, 17})
    print(f'  showers         {(sh(both.symbol_code) == sh(both.pred)).mean():.4f}')
    dry = h[~is_p & ~pred_p]
    print(f'  fog             {((dry.symbol_code == 7) == (dry.pred == 7)).mean():.4f}')
    cl = dry[(dry.symbol_code != 7) & (dry.pred != 7)]
    print(f'  cloud class     {(cl.symbol_code == cl.pred).mean():.4f}')
    print(f'    total cloud only, best mapping  {(cl.cloud_area_fraction.map(tcc_only_symbol) == cl.symbol_code).mean():.4f}')
    print(f'    total cloud only, add-on today  {(cl.cloud_area_fraction.map(addon_cloud_symbol) == cl.symbol_code).mean():.4f}')

    print('\nconfusion on hourly cloud classes (rows SMHI, cols predicted):')
    print(pd.crosstab(cl.symbol_code, cl.pred))
    wrong = df[~df.ok]
    print('\nmost common disagreements (SMHI -> predicted, step hours):')
    print(wrong.groupby(['hours', 'symbol_code', 'pred']).size().sort_values(ascending=False).head(12).to_string())


if __name__ == '__main__':
    main(sys.argv[1])
