"""Exploratory decision trees for SMHI's Wsymb2 assignment.

Usage: venv/bin/python explore.py data.pkl

Splits the symbol into its independent decisions (precip or not, thunder,
intensity, type, showers vs continuous, cloud class, fog) and fits a shallow
decision tree for each, so the learned thresholds can be read off directly.
"""
import sys

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

PRECIP_SYMBOLS = set(range(8, 28))
THUNDER = {11, 21}
SHOWERS = {8, 9, 10, 12, 13, 14, 15, 16, 17}
CONTINUOUS = {18, 19, 20, 22, 23, 24, 25, 26, 27}
INTENSITY = {8: 0, 9: 1, 10: 2, 12: 0, 13: 1, 14: 2, 15: 0, 16: 1, 17: 2,
             18: 0, 19: 1, 20: 2, 22: 0, 23: 1, 24: 2, 25: 0, 26: 1, 27: 2}
KIND = {**{s: 'rain' for s in (8, 9, 10, 18, 19, 20)},
        **{s: 'sleet' for s in (12, 13, 14, 22, 23, 24)},
        **{s: 'snow' for s in (15, 16, 17, 25, 26, 27)}}


def load(path: str) -> pd.DataFrame:
    """The flattened table with derived per-hour precipitation columns."""
    df = pd.read_pickle(path)
    df = df.replace({9999: np.nan})
    for k in ('mean', 'median', 'min', 'max', 'mean_deterministic'):
        df[f'pr_{k}_h'] = df[f'precipitation_amount_{k}'] / df['hours']
    df['lm_cloud'] = df[['low_type_cloud_area_fraction', 'medium_type_cloud_area_fraction']].max(axis=1)
    return df


def tree(df: pd.DataFrame, features: list[str], label: pd.Series, depth: int, title: str) -> None:
    """Fit and print a shallow tree, its training accuracy and class counts."""
    x = df[features].fillna(-1)
    clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=20, random_state=0).fit(x, label)
    print(f'\n=== {title}  (n={len(df)}, accuracy {clf.score(x, label):.4f})')
    print(label.value_counts().to_dict())
    print(export_text(clf, feature_names=features, show_weights=False, decimals=3))


def main(path: str) -> None:
    """Run every exploratory tree."""
    df = load(path)
    print(f'{len(df)} rows, step lengths {df.hours.value_counts().to_dict()}')
    print('symbols:', df.symbol_code.value_counts().sort_index().to_dict())

    precip_feats = ['pr_mean_h', 'pr_median_h', 'pr_min_h', 'pr_max_h', 'pr_mean_deterministic_h',
                    'probability_of_precipitation', 'hours']
    tree(df, precip_feats, df.symbol_code.isin(PRECIP_SYMBOLS), 3, 'precip symbol or not')

    p = df[df.symbol_code.isin(PRECIP_SYMBOLS)]
    tree(p, ['thunderstorm_probability', 'pr_mean_h', 'probability_of_precipitation'],
         p.symbol_code.isin(THUNDER), 2, 'thunder among precip')

    q = p[~p.symbol_code.isin(THUNDER)]
    tree(q, precip_feats, q.symbol_code.map(INTENSITY), 3, 'intensity (0 light, 1 moderate, 2 heavy)')
    tree(q, ['predominant_precipitation_type_at_surface', 'precipitation_frozen_part',
             'probability_of_frozen_precipitation', 'air_temperature'],
         q.symbol_code.map(KIND), 3, 'precip kind')
    tree(q, ['cloud_area_fraction', 'low_type_cloud_area_fraction', 'medium_type_cloud_area_fraction',
             'high_type_cloud_area_fraction', 'lm_cloud', 'probability_of_precipitation', 'pr_mean_h',
             'thunderstorm_probability', 'hours'],
         q.symbol_code.isin(SHOWERS), 3, 'showers vs continuous')

    c = df[df.symbol_code <= 7]
    cloud_feats = ['cloud_area_fraction', 'low_type_cloud_area_fraction', 'medium_type_cloud_area_fraction',
                   'high_type_cloud_area_fraction', 'lm_cloud', 'visibility_in_air', 'relative_humidity',
                   'cloud_base_altitude']
    tree(c, cloud_feats, c.symbol_code == 7, 3, 'fog among dry')
    d = c[c.symbol_code <= 6]
    tree(d, cloud_feats[:5], d.symbol_code, 4, 'cloud class among dry, no fog')


if __name__ == '__main__':
    main(sys.argv[1])
