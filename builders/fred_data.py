#!/usr/bin/env python3
"""
Builder for lectures/fred_data.csv.

Fetches the six FRED series the `risk_aversion_or_mistaken_beliefs` lecture
plots -- three nominal Treasury constant-maturity yields (GS1, GS5, GS10), two
real (TIPS) yields (DFII5, DFII10) and the NBER recession indicator (USREC) --
monthly, over the fixed window 1953-04-01 to 2024-12-01, and writes them as
one date-indexed CSV.

Unlike the BBH files this IS a live-FRED read, deliberately: none of these
series is revised the way the national accounts are. The nominal and real
yields are historical H.15 market rates and USREC is a dummy built from
NBER's published turning points, so the live values are stable -- measured
2026-08-18, a fresh fetch reproduced the committed file byte for byte. The
window end is pinned; this file is a frozen extract, not a tracking snapshot.

Two fetch details that are easy to get wrong:

- FRED publishes DFII5/DFII10 daily. The lecture's file carries their MONTHLY
  AVERAGES, which fredgraph serves with `fq=Monthly&fam=avg`. GS1/GS5/GS10 and
  USREC are monthly at source and need no aggregation.
- fredgraph.csv now titles its date column `observation_date` (it used to be
  `DATE`). The committed file predates the rename, so the index is renamed on
  read; a builder that trusted the served header would change the byte layout.

Stages: fetch -> pre-process -> validate -> write.

Requires pandas.
"""
import io
import os
import urllib.request

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

OUT_FILE = 'fred_data.csv'

FRED_CSV = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
START, END = '1953-04-01', '2024-12-01'

# Monthly at source.
MONTHLY = ['GS1', 'GS5', 'GS10', 'USREC']
# Daily at source; fetched as monthly averages.
DAILY_AVERAGED = ['DFII5', 'DFII10']
# Column order of the published file.
COLUMNS = ['GS1', 'GS5', 'GS10', 'DFII5', 'DFII10', 'USREC']

N_MONTHS = 861                 # 1953-04 .. 2024-12 inclusive, no gaps
# FRED publishes the TIPS yields from 2003-01, so the first 597 months of the
# window are empty in both DFII columns and every other column is complete.
KNOWN_NULLS = {'DFII5': 597, 'DFII10': 597}
TIPS_START = pd.Timestamp('2003-01-01')


def _fetch_series(code):
    url = f'{FRED_CSV}?id={code}&cosd={START}&coed={END}'
    if code in DAILY_AVERAGED:
        url += '&fq=Monthly&fam=avg'
    request = urllib.request.Request(url, headers={'User-Agent': 'qeld-builder'})
    with urllib.request.urlopen(request) as response:
        payload = response.read()
    frame = pd.read_csv(io.BytesIO(payload), index_col=0, parse_dates=True,
                        na_values='.')
    frame.columns = [code]
    return frame


def fetch():
    return pd.concat([_fetch_series(code) for code in COLUMNS], axis=1)


def pre_process(fred):
    fred = fred.loc[START:END]
    fred.index.name = 'DATE'
    fred['USREC'] = fred['USREC'].astype('int64')
    return fred[COLUMNS]


def validate(frame):
    """Refuse to write anything that is not the shape we expect."""
    assert list(frame.columns) == COLUMNS, list(frame.columns)
    assert frame.index.name == 'DATE'

    # 1953-04 .. 2024-12 on an unbroken monthly grid of first-of-month stamps.
    assert len(frame) == N_MONTHS, f'expected {N_MONTHS}, got {len(frame)}'
    assert frame.index[0] == pd.Timestamp(START)
    assert frame.index[-1] == pd.Timestamp(END)
    assert frame.index.is_monotonic_increasing
    assert (frame.index.day == 1).all()
    months = frame.index.year * 12 + frame.index.month
    assert (pd.Series(months).diff().dropna() == 1).all(), 'gap in the grid'

    # Exactly the declared holes, and nowhere else: the TIPS series before
    # 2003-01, full stop.
    nulls = frame.isnull().sum()
    assert dict(nulls[nulls > 0]) == KNOWN_NULLS, dict(nulls[nulls > 0])
    for code in DAILY_AVERAGED:
        assert frame.loc[frame.index < TIPS_START, code].isnull().all()
        assert frame.loc[frame.index >= TIPS_START, code].notnull().all()

    # Units: percent per annum for every yield, 0/1 for the recession dummy.
    # A fetch that silently switched to decimals or to an index would pass the
    # grid checks above and rescale the lecture's figure.
    for code in ['GS1', 'GS5', 'GS10']:
        assert frame[code].between(0.0, 20.0).all(), f'{code} out of band'
    for code in DAILY_AVERAGED:
        assert frame[code].dropna().between(-3.0, 5.0).all(), f'{code} out of band'
    assert set(frame['USREC'].unique()) <= {0, 1}


def run():
    frame = pre_process(fetch())
    validate(frame)
    frame.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE))
    print(f'wrote {OUT_FILE}: {frame.shape[0]} months x {frame.shape[1]} series '
          f'({frame.index[0].date()} .. {frame.index[-1].date()})')


if __name__ == '__main__':
    run()
