#!/usr/bin/env python3
"""
Builder for the World Bank half of the `business_cycle` lecture's data --
three annual tables from WDI, each in the wide layout wbgapi emits (one row
per economy, ISO3 code as the index, country name as `Country`, one `YR<year>`
column per year from 1960):

    business_cycle_data.csv       NY.GDP.MKTP.KD.ZG  real GDP growth, %, for
                                  the nine economies the lecture plots (the
                                  union of its two selections)
    unemployment_rate_annual.csv  SL.UEM.TOTL.NE.ZS  unemployment, % of labour
                                  force (national estimate), USA FRA GBR JPN
    private_credit_to_gdp.csv     FS.AST.PRVT.GD.ZS  domestic credit to the
                                  private sector, % of GDP, GBR

One builder, three files: the "builder writes a set" precedent
(builders/README.md). The two new filenames are PROVISIONAL pending the naming
policy (QuantEcon/data-lectures#113); they are free to change while no lecture
reads them.

These are DYNAMIC SNAPSHOTS (`cadence: annual`). The World Bank revises this
data continuously -- national-accounts rebasing moved GDP growth by up to 1.5
percentage points between the 2025-02 and 2026-09 vintages -- so a refresh is
NOT expected to reproduce the committed bytes and validate() does not ask it
to. What it asserts is the contract a consumer can rely on: the grid, the
fixed economy set, units, structurally-placed nulls, recency, and a bounded
overlap window against the committed snapshot, printed as the review surface
for the refresh PR.

Nulls: WDI series start at different years per economy (UK and French
unemployment begin in 1971 and 1970), GDP growth is undefined in 1960 for
everyone, and the newest year may not be published yet for every series. So
the rule is structural, not a count: a null is allowed only BEFORE an
economy's first observation or in the newest MAX_TRAILING_YEARS, never inside
the series. A gap opening mid-series fails the refresh.

Two provenance dumps (the GDP series' metadata, where the CC BY-4.0 licence
is stated, and the `wb.series.info` listing the lecture teaches) go to
provenance/, with runs of blank lines collapsed. Stages: fetch -> pre-process
-> validate -> write; --out-dir dry-runs; --summary-json writes one summary
PER FILE as a JSON list. Exit 2 on ValidationError, 1 on a fetch failure.
Requires pandas and wbgapi (requirements.txt).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import pandas as pd
import wbgapi as wb

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
PROVENANCE_DIR = os.path.join(REPO_ROOT, 'provenance')

METADATA_FILE = 'business_cycle_metadata.md'
INFO_FILE = 'business_cycle_info.md'
FIRST_YEAR = 1960
YEAR_COL = re.compile(r'^YR(\d{4})$')
MAX_STALENESS_YEARS = 2
MAX_TRAILING_YEARS = 2       # the newest years may be unpublished for a series

# One entry per published file. `economies` is the lecture's selection (the
# union of every call that reads the series); `band` is the unit sanity check
# (percent / percent / percent of GDP); `max_revision` bounds the overlap
# window in the series' own units (GDP growth measured at 1.5 pp routine;
# the credit ratio is rebased in larger steps).
TABLES = [
    {'file': 'business_cycle_data.csv', 'series': 'NY.GDP.MKTP.KD.ZG',
     'economies': ['USA', 'ARG', 'GBR', 'GRC', 'JPN', 'CHN', 'DEU', 'BRA', 'MEX'],
     'band': (-50, 50), 'min_abs_max': 1.0, 'max_revision': 5.0,
     'first_year_null': True},       # growth is undefined in the series' first year
    {'file': 'unemployment_rate_annual.csv', 'series': 'SL.UEM.TOTL.NE.ZS',
     'economies': ['USA', 'FRA', 'GBR', 'JPN'],
     'band': (0, 60), 'min_abs_max': 1.0, 'max_revision': 3.0, 'first_year_null': False},
    {'file': 'private_credit_to_gdp.csv', 'series': 'FS.AST.PRVT.GD.ZS',
     'economies': ['GBR'],
     'band': (0, 400), 'min_abs_max': 1.0, 'max_revision': 25.0, 'first_year_null': False},
]


class ValidationError(Exception):
    """The fetched data broke the published contract -- exit code 2."""


def _check(condition, message):
    if not condition:
        raise ValidationError(message)


def _tidy(text):
    return re.sub(r'\n{3,}', '\n\n', text)


def fetch():
    frames = {t['file']: wb.data.DataFrame(t['series'], t['economies'], labels=True) for t in TABLES}
    metadata = _tidy(str(wb.series.metadata.get(TABLES[0]['series'])))
    info = _tidy(str(wb.series.info(q='GDP growth')))
    return frames, metadata, info


def pre_process(frame):
    frame = frame.copy()
    frame.index.name = 'economy'
    years = sorted(c for c in frame.columns if YEAR_COL.match(c))
    return frame[['Country'] + years]


def _years(frame):
    return [int(YEAR_COL.match(c).group(1)) for c in frame.columns if YEAR_COL.match(c)]


def validate(table, frame, previous=None):
    name = table['file']
    _check(list(frame.columns[:1]) == ['Country'], f'{name}: first columns {list(frame.columns[:3])}')
    years = _years(frame)
    _check(len(years) == len(frame.columns) - 1, f'{name}: non-year column present')
    _check(years[0] == FIRST_YEAR, f'{name}: first year {years[0]}')
    _check(years == list(range(FIRST_YEAR, years[-1] + 1)), f'{name}: gap in the year grid')
    year_cols = [f'YR{y}' for y in years]
    _check(frame.index.name == 'economy', f'{name}: index is {frame.index.name!r}')
    _check(sorted(frame.index) == sorted(table['economies']), f'{name}: economies {sorted(frame.index)}')
    _check(frame['Country'].notnull().all(), f'{name}: a Country label is missing')
    values = frame[year_cols]
    _check(all(pd.api.types.is_float_dtype(values[c]) for c in year_cols), f'{name}: non-float year column')
    _check(values.abs().max().max() >= table['min_abs_max'], f'{name}: values look like ratios')
    lo, hi = table['band']
    _check(values.stack().between(lo, hi).all(), f'{name}: value out of band [{lo}, {hi}]')
    _check(years[-1] >= dt.date.today().year - MAX_STALENESS_YEARS, f'{name}: newest year is {years[-1]}')

    # Nulls: only before an economy's first observation, or in the newest
    # MAX_TRAILING_YEARS; never inside the series. GDP growth additionally has
    # its first year empty for everyone.
    trailing = set(year_cols[-MAX_TRAILING_YEARS:])
    for econ in frame.index:
        row = values.loc[econ]
        first = row.first_valid_index()
        _check(first is not None, f'{name}: {econ} has no data at all')
        inner = row.loc[first:]
        bad = [c for c in inner.index if pd.isnull(inner[c]) and c not in trailing]
        _check(not bad, f'{name}: {econ} has a gap inside its series at {bad[:3]}')
        if table['first_year_null']:
            _check(pd.isnull(row[year_cols[0]]), f'{name}: {econ} has a value in {year_cols[0]}')

    summary = {
        'dataset': name,
        'builder': os.path.relpath(os.path.abspath(__file__), REPO_ROOT),
        'rows': int(frame.shape[0]),
        'columns': int(frame.shape[1]),
        'date_range': {'start': years[0], 'end': years[-1]},
        'overlap': None,
    }
    if previous is not None:
        prev_years = [f'YR{y}' for y in _years(previous)]
        _check(set(prev_years) <= set(year_cols), f'{name}: a year column disappeared')
        common = [e for e in previous.index if e in frame.index]
        _check(common, f'{name}: no economy in common with the previous snapshot')
        old = previous.loc[common, prev_years]
        new = frame.loc[common, prev_years]
        _check(not (old.notnull() & new.isnull()).any().any(), f'{name}: a populated cell went empty')
        diff = (old - new).abs()
        changed = int((diff > 1e-9).sum().sum())
        worst = float(diff.max().max()) if diff.notnull().any().any() else 0.0
        summary['overlap'] = {
            'window': f'{prev_years[0]}..{prev_years[-1]}',
            'previous_end': _years(previous)[-1],
            'cells_total': int(old.notnull().sum().sum()),
            'cells_revised': changed,
            'max_abs_change': round(worst, 4),
            'new_columns': sorted(set(year_cols) - set(prev_years)),
            'new_economies': sorted(set(frame.index) - set(previous.index)),
        }
        print(f'{name}: overlap {prev_years[0]}..{prev_years[-1]} over {common}: {changed} cells revised, '
              f'max |change| {worst:.3f}; new columns {summary["overlap"]["new_columns"] or "none"}; '
              f'new economies {summary["overlap"]["new_economies"] or "none"}')
        _check(worst <= table['max_revision'], f'{name}: revision of {worst:.3f} exceeds {table["max_revision"]}')
    return summary


def _atomic_write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, path)


def run(out_dir=None, summary_json=None):
    data_dir = out_dir or PUBLISHED_DIR
    prov_dir = out_dir or PROVENANCE_DIR
    frames, metadata, info = fetch()
    summaries, outputs = [], {}
    for table in TABLES:
        previous_path = os.path.join(PUBLISHED_DIR, table['file'])
        previous = pd.read_csv(previous_path, index_col=0) if os.path.exists(previous_path) else None
        frame = pre_process(frames[table['file']])
        summaries.append(validate(table, frame, previous))
        outputs[table['file']] = frame
    # Validate everything, then write everything: a failure in the third table
    # must not leave the first two refreshed and the set out of step.
    if summary_json:
        _atomic_write(summary_json, json.dumps(summaries, indent=1) + '\n')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(prov_dir, exist_ok=True)
    for name, frame in outputs.items():
        _atomic_write(os.path.join(data_dir, name), frame.to_csv())
        years = _years(frame)
        print(f'wrote {name}: {frame.shape[0]} economies x {len(years)} years ({years[0]} .. {years[-1]}) -> {data_dir}')
    _atomic_write(os.path.join(prov_dir, METADATA_FILE), metadata)
    _atomic_write(os.path.join(prov_dir, INFO_FILE), info)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir', help='write outputs here instead of lectures/ and provenance/')
    ap.add_argument('--summary-json', help='also write the run summaries (a JSON list) here')
    args = ap.parse_args()
    try:
        run(args.out_dir, args.summary_json)
    except ValidationError as exc:
        print(f'::error::business_cycle: validation failed -- {exc}', file=sys.stderr)
        sys.exit(2)
