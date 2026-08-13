"""
Builder for lectures/NEWQDATA.csv.

Converts Cogley and Sargent's MATLAB data file for "Drifts and Volatilities:
Monetary Policies and Outcomes in the Post WWII U.S." into the CSV the
`phillips_drifts_volatilities` lecture reads. Four quarterly series over
1948Q2-2000Q4: the quarter index, the three-month Treasury bill rate,
the civilian unemployment rate and CPI inflation.

This is a value-preserving container conversion and nothing else -- .MAT to
.csv, no filtering, no rescaling, no reordering. That is why the published CSV
can be reproduced byte for byte from the committed input.

READS ITS INPUT FROM sources/, WHICH IS THE EXCEPTION, NOT THE RULE.
AGENTS.md permits it only when the input cannot be re-fetched, and this one
cannot: the authors' MATLAB directory is not published by either author, by the
Review of Economic Dynamics, or by RePEc, and no Wayback capture of it exists.
Searched to exhaustion 2026-08-13 -- see sources/README.md. The only copy
located anywhere was a third-party GitHub mirror, and a builder that depends on
a stranger's repository is exactly the fragility sources/ exists to remove.

Stages: fetch -> pre-process -> validate -> write.
"""

import os

import pandas as pd
from scipy.io import loadmat

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
SOURCES_DIR = os.path.join(REPO_ROOT, 'sources')

SOURCE_FILE = 'NEWQDATA.MAT'

# The .MAT holds four bare arrays under these names, in this order. The output
# column order is the input order -- see validate().
COLUMNS = ['date', 'y3', 'ur', 'dp']

# 1948Q2 to 2000Q4 inclusive, quarterly, no gaps.
N_QUARTERS = 211
FIRST_QUARTER = 1948.25
LAST_QUARTER = 2000.75

OUT_FILE = 'NEWQDATA.csv'


def fetch():
    return loadmat(os.path.join(SOURCES_DIR, SOURCE_FILE))


def pre_process(raw):
    # Each array is (211, 1); ravel to 1-D so the frame is 211 rows, not 211
    # columns of one element.
    return pd.DataFrame({name: raw[name].ravel() for name in COLUMNS})


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == COLUMNS
    assert len(df) == N_QUARTERS, f'expected {N_QUARTERS} quarters, got {len(df)}'
    assert not df.isnull().values.any()
    assert (df.dtypes == 'float64').all()

    # The quarter index is the file's only self-describing column: it must be
    # an unbroken 0.25 grid over the paper's sample. A silently truncated or
    # re-based input fails here rather than in a lecture build.
    assert df['date'].iloc[0] == FIRST_QUARTER
    assert df['date'].iloc[-1] == LAST_QUARTER
    assert ((df['date'].diff().iloc[1:] - 0.25).abs() < 1e-9).all()

    # Rates are stored as fractions, not percentages. A vintage that switched
    # units would sail through every check above.
    assert df['ur'].between(0.02, 0.12).all(), 'unemployment is not a fraction'
    assert df['y3'].between(0.0, 0.06).all(), 'T-bill rate is not a fraction'
    assert df['dp'].between(-0.02, 0.06).all(), 'inflation is not a fraction'


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} quarters, '
          f'{df["date"].iloc[0]} to {df["date"].iloc[-1]}')


if __name__ == '__main__':
    run()
