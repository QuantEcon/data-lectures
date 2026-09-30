"""
Builder for lectures/us_household_net_worth_2022.csv.

Extracts household net worth, with survey weights, from the Federal Reserve
Board's 2022 Survey of Consumer Finances (SCF) summary extract public data
(Stata file rscfp2022.dta inside scfp2022s.zip).

The extract keeps four of the summary file's columns: the household id (yy1),
the household-implicate id (y1), the weight (wgt) and net worth (networth,
2022 dollars). Every household appears five times, once per multiple-imputation
implicate, so the file has 4,595 x 5 = 22,975 rows. The summary extract's wgt
is already divided by 5, so summing wgt over all rows gives the population
number of households.

Stata stores yy1 as int16 and y1 as int32; both are cast to int64 before any
arithmetic, so they are written as plain integers and cannot overflow.

The Fed server refuses the default urllib user agent (HTTP 403), so the fetch
sends a browser-like one.

Stages: fetch -> pre-process -> validate -> write.
"""

import io
import os
import urllib.request
import zipfile

import pandas as pd
import yaml

from _validate import validate as validate_schema

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

SOURCE_URL = 'https://www.federalreserve.gov/econres/files/scfp2022s.zip'
MEMBER = 'rscfp2022.dta'
USER_AGENT = 'Mozilla/5.0'

OUT_FILE = 'us_household_net_worth_2022.csv'
COLUMNS = ['yy1', 'y1', 'wgt', 'networth']

N_HOUSEHOLDS = 4595           # 4,602 interviewed, 7 removed for disclosure
N_IMPLICATES = 5
POPULATION = (130e6, 133e6)   # sum of wgt: US households in 2022 (~131.3M)


def fetch():
    """Download the zip and return the Stata file's bytes."""
    request = urllib.request.Request(SOURCE_URL,
                                     headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return archive.read(MEMBER)


def pre_process(raw):
    """Keep four columns, ids as int64, one row per household-implicate."""
    df = pd.read_stata(io.BytesIO(raw), columns=COLUMNS,
                       convert_categoricals=False)
    df = df.astype({'yy1': 'int64', 'y1': 'int64',
                    'wgt': 'float64', 'networth': 'float64'})
    return df.sort_values('y1').reset_index(drop=True)


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    with open(os.path.join(PUBLISHED_DIR, OUT_FILE + '.yml')) as f:
        manifest = yaml.safe_load(f)
    validate_schema(df, manifest)

    assert list(df.columns) == COLUMNS
    assert not df.isnull().values.any()
    assert len(df) == N_HOUSEHOLDS * N_IMPLICATES, len(df)
    counts = df['yy1'].value_counts()
    assert len(counts) == N_HOUSEHOLDS, len(counts)
    assert (counts == N_IMPLICATES).all()
    # y1 = 10 * yy1 + implicate number, implicates 1..5
    implicate = df['y1'] - 10 * df['yy1']
    assert implicate.between(1, N_IMPLICATES).all()
    assert df['y1'].is_unique and df['y1'].is_monotonic_increasing
    assert (df['wgt'] > 0).all()
    total = df['wgt'].sum()
    assert POPULATION[0] < total < POPULATION[1], total
    return total


def run():
    df = pre_process(fetch())
    total = validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} rows, '
          f'{df["yy1"].nunique()} households, '
          f'sum of wgt {total / 1e6:.2f} million')


if __name__ == '__main__':
    run()
