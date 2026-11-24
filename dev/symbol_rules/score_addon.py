"""Score the add-on's _derive_symbol against SMHI's symbols in DATA.pkl.

Usage: venv/bin/python score_addon.py data.pkl ../../resources/lib
"""
import sys

import pandas as pd


def main(path: str, lib: str) -> None:
    """Derive a symbol for every step with the add-on's model and compare."""
    # Inputs are what the add-on would know: the precipitation rate (SMHI's
    # median per hour), total cloud, visibility, precipitation type and
    # thunder probability. The forecast symbol itself is left out.
    sys.path.insert(0, lib)
    from smhi.model import WxObs
    from smhi.symbols import precip_from_ptype
    df = pd.read_pickle(path)
    pred = [WxObs(precip_intensity=r.precipitation_amount_median / r.hours,
                  precip_type=precip_from_ptype(r.predominant_precipitation_type_at_surface),
                  cloud_cover=r.cloud_area_fraction, visibility=r.visibility_in_air,
                  thunder_prob=r.thunderstorm_probability, temperature=r.air_temperature).effective_symbol
            for r in df.itertuples()]
    ok = pd.Series([p is not None and int(p) == s for p, s in zip(pred, df.symbol_code)])
    print(f'{lib}: overall {ok.mean():.4f}, hourly {ok[df.hours.to_numpy() == 1].mean():.4f}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
