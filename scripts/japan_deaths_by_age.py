"""
Builder for lectures/japan_deaths_by_age.csv.

Extracts the age distribution of deaths in Japan in a single year from the UN
World Population Prospects (WPP) "deaths by single age and sex" release.

The upstream file covers every location and every year from 1950, and is ~45 MB
gzipped; we stream it in chunks and keep one country-year. Death counts are
published in thousands, so the counts are scaled to persons and rounded to
integers.

Stages: fetch -> pre-process -> validate -> write.
"""

import os

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

SOURCE_URL = (
    'https://population.un.org/wpp/assets/Excel%20Files/'
    '1_Indicator%20(Standard)/CSV_FILES/'
    'WPP2024_DeathsBySingleAgeSex_Medium_1950-2023.csv.gz'
)

ISO3 = 'JPN'
YEAR = 2023
OUT_FILE = 'japan_deaths_by_age.csv'

USE_COLS = ['ISO3_code', 'Location', 'Time', 'AgeGrpStart',
            'DeathMale', 'DeathFemale', 'DeathTotal']


def fetch():
    """Stream the upstream release, keeping only the country-year we need."""
    chunks = pd.read_csv(SOURCE_URL, usecols=USE_COLS,
                         chunksize=500_000, low_memory=False)
    keep = [c[(c['ISO3_code'] == ISO3) & (c['Time'] == YEAR)] for c in chunks]
    return pd.concat(keep, ignore_index=True)


def pre_process(raw):
    """Scale thousands to persons and keep age plus the three count columns."""
    df = pd.DataFrame({
        'age': raw['AgeGrpStart'].astype(int),
        'deaths_male': (raw['DeathMale'] * 1000).round().astype(int),
        'deaths_female': (raw['DeathFemale'] * 1000).round().astype(int),
        'deaths_total': (raw['DeathTotal'] * 1000).round().astype(int),
    })
    return df.sort_values('age').reset_index(drop=True)


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == ['age', 'deaths_male', 'deaths_female',
                                'deaths_total']
    assert len(df) == 101, f'expected ages 0-100+, got {len(df)} rows'
    assert df['age'].tolist() == list(range(101))
    assert not df.isnull().values.any()
    assert (df[['deaths_male', 'deaths_female', 'deaths_total']] >= 0).all().all()
    # The three counts are rounded independently, so allow a rounding slack.
    gap = (df['deaths_male'] + df['deaths_female'] - df['deaths_total']).abs()
    assert gap.max() <= 1, f'male + female != total by {gap.max()}'
    total = df['deaths_total'].sum()
    assert 1_000_000 < total < 2_000_000, f'implausible death total {total}'


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} rows, '
          f'{df["deaths_total"].sum():,} deaths')


if __name__ == '__main__':
    run()
