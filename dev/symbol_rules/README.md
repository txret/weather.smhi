# How SMHI assigns weather symbols

SMHI's snow1g forecast gives a weather symbol (`symbol_code`, Wsymb2 1–27)
for each step, but stations don't. To derive a matching symbol from station
observations (`WxObs._derive_symbol` in `resources/lib/smhi/model.py`), the
rules were inferred by comparing `symbol_code` with the other forecast
parameters. The data is 1500 random grid points × 86 steps of the snow1g run
of 2026-11-24 09:15 UTC: 129 000 steps.

## Inferred rules

Applied in this order, the first match wins:

| Decision                  | Rule                                                                                                                   | Agreement             |
|---------------------------|------------------------------------------------------------------------------------------------------------------------|-----------------------|
| Precipitation or not      | step median `precipitation_amount_median` ≥ 0.1 mm, for any step length (not the probability of precipitation)         | 100% (1 miss)         |
| Thunder (11 / 21)         | precipitation is rain and `thunderstorm_probability` ≥ 50%; snow is never replaced, dry steps never get it             | only 9 cases          |
| Rain / sleet / snow       | `predominant_precipitation_type_at_surface`: 1, 3, 11, 12 → rain; 5 → snow; 6 (wet snow) → sleet. Frozen part unused   | 100%                  |
| Light / moderate          | median per hour ≥ 0.5 mm/h → moderate, the same for rain, sleet and snow                                               | 100%                  |
| Heavy                     | never occurred: unknown                                                                                                | –                     |
| Showers vs continuous     | total cloud < 8 octas → showers (always); at 8 octas mostly continuous, probably decided on the unrounded value        | 92%                   |
| Fog (7)                   | visibility < 1 km                                                                                                      | 99.97%                |
| Cloud class               | eff = max(low, medium) + 0.75 × (total − max(low, medium)); ≥ 7.25 → 6, ≥ 5.5 → 4, ≥ 3.25 → 3, ≥ 1.5 → 2, else 1        | 90.7% (ceiling ≈ 92%) |
| Cloud class, total only   | 0–1 → 1, 2–3 → 2, 4–5 → 3, 6–7 → 4, 8 → 6 (what the add-on uses: stations report only total cloud)                     | 89%                   |

Other findings:

* "Cloudy" (5) is never used.
* Codes 7 (rain/snow mix) and 8 (ice pellets) never occurred.
* 12-hour steps follow a different, period-based scheme. They are never clear or nearly clear, and only 80% agree with the rules above.
* The cloud classes have noise that the API's rounded octas can't explain. Some of it correlates with the previous hour's cloud cover.

Overall, `rules.py` reproduces SMHI's symbol for 89.5% of steps. The add-on's
`_derive_symbol`, which uses total cloud only, matches 84.9% (89.4% on hourly
steps); before this work it matched 63.6% (70.9%).

Limitations: this is one run of late-November weather. Heavy precipitation,
ptype 7/8 and most thunder situations are missing, so those rules (and the
add-on's heavy cut-offs, kept from before) are not verified.

## Files

| File             | Purpose                                                                                     |
|------------------|---------------------------------------------------------------------------------------------|
| `fetch.py`       | downloads point forecasts for a random sample of grid points into `raw/points/<run>/`       |
| `flatten.py`     | turns the cached forecasts into one table, `data.pkl` (a row per point and step)            |
| `explore.py`     | shallow decision trees per decision, to read off the thresholds                             |
| `rules.py`       | the inferred ruleset, scored against SMHI per step length and per decision                  |
| `score_addon.py` | scores the add-on's `WxObs.effective_symbol` against SMHI on the same data                  |
| `raw/`           | `multipoint.json` (grid coordinates), `parameter.json`, cached point forecasts (gzip JSON) |
| `data.pkl`       | the flattened table (pandas pickle; can be rebuilt with `flatten.py`)                       |

## Reproducing

```sh
python3 -m venv venv && venv/bin/pip install pandas scikit-learn
python3 -I fetch.py raw 1500                 # only downloads what is not cached; a new run goes in its own folder
venv/bin/python -I flatten.py raw data.pkl
venv/bin/python explore.py data.pkl
venv/bin/python rules.py data.pkl
venv/bin/python score_addon.py data.pkl ../../resources/lib
```

To fetch a fresh `raw/multipoint.json` (8.8 MB), request
`https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/multipoint.json`
with gzip accepted (for example `curl --compressed`).
