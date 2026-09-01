#!/usr/bin/env python3
"""
Builder for lectures/us_business_cycle_monthly.csv -- the FRED half of the
`business_cycle` lecture's data, as one composite monthly file.

Six FRED series on one monthly DATE index from 1919-01 (the earliest month
the lecture asks for, INDPRO's start) to the newest month FRED carries:

    UNRATE            civilian unemployment rate, %, monthly from 1948-01
    USREC             NBER recession indicator, 0/1, monthly (from 1854)
    UMCSENT           Michigan consumer sentiment, index, irregular from
                      1952-11 and MONTHLY only from 1978-01 -- the lecture
                      reads it from 1978, and validate() treats the earlier
                      gaps as structural
    CPILFESL          CPI less food and energy, index 1982-84=100, from 1957-01
    INDPRO            industrial production index, 2017=100, from 1919-01
    M0892AUSM156SNBR  unemployment rate 1929-04..1942-06 (NBER Macrohistory),
                      the historical series the lecture splices before UNRATE

Why one file rather than six: the lecture reads them together, and a single
URL with the lecture's own variable names as columns is what keeps the wasm
edition readable (QuantEcon/lecture-wasm#70). The fetch is `builders/_fred.py`;
this file is the contract.

Nulls are structural and declared, not tolerated: each series is empty before
its first observation; UMCSENT is sparse before 1978-01; the historical series
is empty after 1942-06; and UNRATE and CPILFESL share ONE hole, 2025-10, the
month the 2025 federal shutdown stopped BLS publishing. validate() asserts
exactly those and no others, so a new hole -- another shutdown, a FRED outage
served as `.` -- fails the refresh for a human to look at rather than shipping.

Revisions: CPILFESL and INDPRO are revised (seasonal factors yearly, INDPRO's
annual benchmark), UNRATE occasionally, USREC and the historical series never.
validate() bounds each series' revisions in the overlap window and prints the
summary -- the review surface for the refresh PR.

Stages: fetch -> pre-process -> validate -> write. --out-dir dry-runs,
--summary-json writes the run summary. Exit 2 on ValidationError, 1 on a
fetch failure. Requires pandas.
"""
import argparse
import datetime as dt
import json
import os
import sys

import pandas as pd

from _fred import Fred

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

OUT_FILE = 'us_business_cycle_monthly.csv'
START = '1919-01-01'
COLUMNS = ['UNRATE', 'USREC', 'UMCSENT', 'CPILFESL', 'INDPRO', 'M0892AUSM156SNBR']

# First observation of each series, as published; a series whose start moves
# is a different series.
FIRST_OBS = {'UNRATE': '1948-01-01', 'USREC': START, 'UMCSENT': '1952-11-01',
             'CPILFESL': '1957-01-01', 'INDPRO': START, 'M0892AUSM156SNBR': '1929-04-01'}
# Where each series becomes gap-free monthly. UMCSENT is quarterly/irregular
# before 1978; the historical unemployment series ends in 1942-06.
MONTHLY_FROM = {**{c: FIRST_OBS[c] for c in COLUMNS}, 'UMCSENT': '1978-01-01'}
LAST_OBS = {'M0892AUSM156SNBR': '1942-06-01'}
# Holes inside a series' monthly span that are known and accepted.
KNOWN_HOLES = {'UNRATE': ['2025-10-01'], 'CPILFESL': ['2025-10-01']}
# Value bands: percent, 0/1, index levels.
BANDS = {'UNRATE': (0, 30), 'USREC': (0, 1), 'UMCSENT': (20, 150),
         'CPILFESL': (20, 1000), 'INDPRO': (1, 300), 'M0892AUSM156SNBR': (0, 40)}
# Overlap-window bound per series, in the series' own units.
MAX_REVISION = {'UNRATE': 0.5, 'USREC': 0, 'UMCSENT': 5.0,
                'CPILFESL': 3.0, 'INDPRO': 5.0, 'M0892AUSM156SNBR': 0}
MAX_STALENESS_MONTHS = 3


class ValidationError(Exception):
    """The fetched data broke the published contract -- exit code 2."""


def _check(condition, message):
    if not condition:
        raise ValidationError(message)


def fetch():
    return Fred().frame(COLUMNS, start=START)


def pre_process(frame):
    # Pure: no casts that can raise. USREC stays float here (a `.` from FRED
    # would be NaN) so that validate() is what rejects a hole in it, with
    # exit code 2, rather than an astype() raising ValueError with exit 1.
    frame = frame.loc[START:].copy()
    frame.index.name = 'DATE'
    return frame[COLUMNS]


def _months(index):
    return pd.Series(index.year * 12 + index.month, index=index)


def validate(frame, previous=None):
    _check(list(frame.columns) == COLUMNS, f'columns {list(frame.columns)}')
    _check(frame.index.name == 'DATE', f'index is {frame.index.name!r}')
    _check(frame.index[0] == pd.Timestamp(START), f'starts {frame.index[0].date()}')
    _check(frame.index.is_monotonic_increasing and (frame.index.day == 1).all(), 'not first-of-month')
    _check((_months(frame.index).diff().dropna() == 1).all(), 'gap in the monthly grid')
    today = dt.date.today()
    age = (today.year * 12 + today.month) - (frame.index[-1].year * 12 + frame.index[-1].month)
    _check(age <= MAX_STALENESS_MONTHS, f'newest month is {frame.index[-1].date()}')

    for col in COLUMNS:
        s = frame[col]
        first = pd.Timestamp(FIRST_OBS[col])
        _check(s.loc[:first - pd.offsets.MonthBegin(1)].isnull().all() if first > frame.index[0] else True,
               f'{col}: observed before its first observation {first.date()}')
        _check(s.first_valid_index() == first, f'{col}: first observation is {s.first_valid_index()}, not {first.date()}')
        monthly_from = pd.Timestamp(MONTHLY_FROM[col])
        last = pd.Timestamp(LAST_OBS.get(col, frame.index[-1]))
        span = s.loc[monthly_from:last]
        holes = [str(d.date()) for d in span[span.isnull()].index]
        _check(holes == KNOWN_HOLES.get(col, []), f'{col}: holes {holes} != known {KNOWN_HOLES.get(col, [])}')
        if col in LAST_OBS:
            _check(s.loc[last + pd.offsets.MonthBegin(1):].isnull().all(), f'{col}: observed after {last.date()}')
        lo, hi = BANDS[col]
        _check(s.dropna().between(lo, hi).all(), f'{col}: out of band [{lo}, {hi}]')
    _check(frame['USREC'].notnull().all(), 'USREC has a missing month')
    _check(set(frame['USREC'].unique()) <= {0, 1}, 'USREC not 0/1')

    summary = {
        'dataset': OUT_FILE,
        'builder': os.path.relpath(os.path.abspath(__file__), REPO_ROOT),
        'rows': int(frame.shape[0]),
        'columns': int(frame.shape[1]),
        'date_range': {'start': str(frame.index[0].date()), 'end': str(frame.index[-1].date())},
        'overlap': None,
    }
    if previous is not None:
        _check(list(previous.columns) == COLUMNS, 'previous snapshot has different columns')
        common = previous.index.intersection(frame.index)
        old, new = previous.loc[common], frame.loc[common]
        _check(not (old.notnull() & new.isnull()).any().any(), 'a populated cell went empty')
        diff = (old - new).abs()
        worst = {c: float(diff[c].max()) if diff[c].notnull().any() else 0.0 for c in COLUMNS}
        changed = int((diff > 1e-9).sum().sum())
        summary['overlap'] = {
            'window': f'{common[0].date()}..{common[-1].date()}',
            'previous_end': str(previous.index[-1].date()),
            'cells_total': int(old.notnull().sum().sum()),
            'cells_revised': changed,
            'max_abs_change': round(max(worst.values()), 4),
            'max_abs_change_by_series': {c: round(v, 4) for c, v in worst.items()},
            'new_columns': [],
        }
        print(f'overlap window {common[0].date()}..{common[-1].date()}: {changed} cells revised; '
              f'max |change| by series {summary["overlap"]["max_abs_change_by_series"]}')
        for c in COLUMNS:
            _check(worst[c] <= MAX_REVISION[c], f'{c}: revision {worst[c]:.4f} exceeds {MAX_REVISION[c]}')
    return summary


def _atomic_write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, path)


def run(out_dir=None, summary_json=None):
    data_dir = out_dir or PUBLISHED_DIR
    previous_path = os.path.join(PUBLISHED_DIR, OUT_FILE)
    previous = (pd.read_csv(previous_path, index_col=0, parse_dates=True)
                if os.path.exists(previous_path) else None)
    frame = pre_process(fetch())
    summary = validate(frame, previous)
    frame['USREC'] = frame['USREC'].astype('int64')   # safe: validated complete and 0/1
    if summary_json:
        _atomic_write(summary_json, json.dumps(summary, indent=1) + '\n')
    os.makedirs(data_dir, exist_ok=True)
    _atomic_write(os.path.join(data_dir, OUT_FILE), frame.to_csv())
    print(f'wrote {OUT_FILE}: {frame.shape[0]} months x {frame.shape[1]} series '
          f'({frame.index[0].date()} .. {frame.index[-1].date()}) -> {data_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir')
    ap.add_argument('--summary-json')
    args = ap.parse_args()
    try:
        run(args.out_dir, args.summary_json)
    except ValidationError as exc:
        print(f'::error::{OUT_FILE}: validation failed -- {exc}', file=sys.stderr)
        sys.exit(2)
