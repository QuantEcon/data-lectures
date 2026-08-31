#!/usr/bin/env python3
"""
Builder for lectures/business_cycle_data.csv.

Fetches annual real GDP growth (World Bank WDI series NY.GDP.MKTP.KD.ZG) for
five economies -- USA, ARG, GBR, GRC and JPN -- exactly as the intro
`business_cycle` lecture fetches it live with wbgapi, and writes it as one
wide CSV: one row per economy, one `YR<year>` column per year from 1960.

This is the repo's one DYNAMIC SNAPSHOT (`class: dynamic-snapshot`,
`cadence: annual` in the manifest). Unlike the frozen extracts beside it, the
World Bank revises this series continuously -- national-accounts rebasing
moves historical growth rates by up to about 1.5 percentage points -- so a
refresh is NOT expected to reproduce the committed bytes, and validate() does
not ask it to. Measured 2026-09-01: 63 of the 64 overlapping year columns had
at least one revised cell (236 of 320 cells; median change 0.0, 99th
percentile 1.0, maximum 1.5), and two new columns (YR2024, YR2025) had
appeared. That delta is recorded in the manifest's integrity.upstream block
and in the register at QuantEcon/data-lectures#39.

What validate() DOES assert is the contract a consumer can rely on: the
shape, the column grid, the fixed set of economies, percent units, the one
structural null (YR1960, growth being undefined in the series' first year),
recency, and -- against the previously committed snapshot -- that no revision
exceeds MAX_REVISION percentage points and no previously populated cell has
gone empty. It prints the overlap-window summary on every run; that summary
is the review surface for a refresh PR (PLAN Phase 5).

Two provenance dumps are written beside the data, to provenance/ (NOT
lectures/ -- they are not datasets; QuantEcon/data-lectures#13): the series
metadata, which is where the CC BY-4.0 licence the manifest cites is stated,
and the `wb.series.info(q='GDP growth')` listing the lecture teaches.

Stages: fetch -> pre-process -> validate -> write. Writes only on validation
pass, so a failed refresh leaves the last-good snapshot in place.

Usage:
    python builders/business_cycle.py              # refresh in place
    python builders/business_cycle.py --out-dir D  # write everything to D
                                                   # (a dry run; validates
                                                   # against lectures/ still)

Requires pandas and wbgapi (requirements.txt).
"""
import argparse
import datetime as dt
import os
import re

import pandas as pd
import wbgapi as wb

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
PROVENANCE_DIR = os.path.join(REPO_ROOT, 'provenance')

OUT_FILE = 'business_cycle_data.csv'
METADATA_FILE = 'business_cycle_metadata.md'
INFO_FILE = 'business_cycle_info.md'

SERIES = 'NY.GDP.MKTP.KD.ZG'
# The five economies the lecture plots, in the order it names them. wbgapi
# returns rows in its own order (JPN, GRC, GBR, ARG, USA on every run so far);
# that order is kept as returned so a refresh diff is values-only.
ECONOMIES = ['USA', 'ARG', 'GBR', 'GRC', 'JPN']
FIRST_YEAR = 1960
YEAR_COL = re.compile(r'^YR(\d{4})$')

# Overlap-window policy for a revised aggregate. The World Bank's routine
# revisions to this series have measured at most 1.5 pp (2026-09-01, 2025-02
# vintage vs live); a change past this bound is a rebasing, a units switch or
# an upstream defect, and wants a human before it ships.
MAX_REVISION = 5.0          # percentage points, any single cell
# Percent units: a fetch that came back as a ratio (0.02 for 2%) or as an
# index level would pass every shape check and rescale the lecture's figure.
MIN_ABS_MAX, MAX_ABS = 1.0, 50.0
# A refresh whose newest year is older than this many years behind today
# means the fetch returned a stale or truncated panel.
MAX_STALENESS_YEARS = 2


def fetch():
    """Live WDI, exactly the lecture's own three calls."""
    frame = wb.data.DataFrame(SERIES, ECONOMIES, labels=True)
    metadata = str(wb.series.metadata.get(SERIES))
    info = str(wb.series.info(q='GDP growth'))
    return frame, metadata, info


def pre_process(frame):
    # wbgapi's index is the ISO3 code, named `economy`; `Country` is the label
    # column `labels=True` adds. Keep the layout the lecture (and the
    # committed file) uses: Country first, then the year columns ascending.
    frame = frame.copy()
    frame.index.name = 'economy'
    years = sorted(c for c in frame.columns if YEAR_COL.match(c))
    return frame[['Country'] + years]


def _years(frame):
    return [int(YEAR_COL.match(c).group(1)) for c in frame.columns if YEAR_COL.match(c)]


def validate(frame, previous=None):
    """Refuse to write anything that is not the shape we expect."""
    # Grid: Country, then YR<first>..YR<last> with no gap.
    assert list(frame.columns[:1]) == ['Country'], list(frame.columns[:3])
    years = _years(frame)
    assert len(years) == len(frame.columns) - 1, 'non-year column present'
    assert years[0] == FIRST_YEAR, years[0]
    assert years == list(range(FIRST_YEAR, years[-1] + 1)), 'gap in the year grid'
    year_cols = [f'YR{y}' for y in years]

    # Economies: exactly the five, one row each.
    assert frame.index.name == 'economy'
    assert sorted(frame.index) == sorted(ECONOMIES), sorted(frame.index)
    assert frame['Country'].notnull().all()

    # Dtypes and units.
    values = frame[year_cols]
    assert all(pd.api.types.is_float_dtype(values[c]) for c in year_cols), 'non-float year column'
    assert values.abs().max().max() >= MIN_ABS_MAX, 'values look like ratios, not percent'
    assert values.abs().max().max() <= MAX_ABS, 'growth rate out of band'

    # The one structural null: growth is undefined in the series' first year.
    nulls = values.isnull().sum()
    assert dict(nulls[nulls > 0]) == {f'YR{FIRST_YEAR}': len(ECONOMIES)}, dict(nulls[nulls > 0])

    # Recency.
    assert years[-1] >= dt.date.today().year - MAX_STALENESS_YEARS, f'newest year is {years[-1]}'

    # Overlap window against the last-good snapshot: revisions are expected,
    # bounded, and reported; a lost observation or a rescale is not.
    if previous is not None:
        prev_years = [f'YR{y}' for y in _years(previous)]
        assert set(prev_years) <= set(year_cols), 'a year column disappeared'
        assert sorted(previous.index) == sorted(frame.index), 'the economy set changed'
        old = previous.loc[frame.index, prev_years]
        new = frame.loc[frame.index, prev_years]
        assert not (old.notnull() & new.isnull()).any().any(), 'a populated cell went empty'
        diff = (old - new).abs()
        changed = int((diff > 1e-9).sum().sum())
        worst = float(diff.max().max())
        print(f'overlap window {prev_years[0]}..{prev_years[-1]}: '
              f'{changed} of {diff.size} cells revised, max |change| {worst:.3f} pp; '
              f'new columns: {sorted(set(year_cols) - set(prev_years)) or "none"}')
        assert worst <= MAX_REVISION, f'revision of {worst:.3f} pp exceeds {MAX_REVISION}'


def run(out_dir=None):
    data_dir = out_dir or PUBLISHED_DIR
    prov_dir = out_dir or PROVENANCE_DIR
    previous_path = os.path.join(PUBLISHED_DIR, OUT_FILE)
    previous = (pd.read_csv(previous_path, index_col=0)
                if os.path.exists(previous_path) else None)

    frame, metadata, info = fetch()
    frame = pre_process(frame)
    validate(frame, previous)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(prov_dir, exist_ok=True)
    frame.to_csv(os.path.join(data_dir, OUT_FILE))
    with open(os.path.join(prov_dir, METADATA_FILE), 'w') as f:
        f.write(metadata)
    with open(os.path.join(prov_dir, INFO_FILE), 'w') as f:
        f.write(info)
    years = _years(frame)
    print(f'wrote {OUT_FILE}: {frame.shape[0]} economies x {len(years)} years '
          f'({years[0]} .. {years[-1]}) -> {data_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir', help='write outputs here instead of lectures/ and provenance/')
    run(ap.parse_args().out_dir)
