"""
Builder for lectures/us_adult_heights.csv.

Extracts standing height by sex for US adults from two NHANES cycles,
2015-2016 (suffix I) and 2017-2018 (suffix J).

Each cycle ships demographics (DEMO) and body measures (BMX) as separate SAS
transport files, joined on the respondent id SEQN. The extract keeps adults
aged 20 and over with a recorded height, excluding pregnant respondents, and
writes males followed by females.

This builder was recovered after the fact: the CSV was first assembled for
lecture-python-intro#790 without a committed script. Its output is
byte-identical to that file (sha256 6240535326bc7e23...), so the filters below
are the original ones, not a reinterpretation.

Stages: fetch -> pre-process -> validate -> write.
"""

import os

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

BASE_URL = 'https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public'

# (demographics file, body measures file, cycle directory)
CYCLES = [('DEMO_I', 'BMX_I', '2015'),
          ('DEMO_J', 'BMX_J', '2017')]

OUT_FILE = 'us_adult_heights.csv'

MIN_AGE = 20            # RIDAGEYR — "adult" for this extract
PREGNANT = 1            # RIDEXPRG code for "pregnant at exam"
MALE, FEMALE = 1, 2     # RIAGENDR codes


def fetch():
    """Join demographics to body measures, one frame per cycle."""
    frames = []
    for demo, bmx, cycle in CYCLES:
        dem = pd.read_sas(f'{BASE_URL}/{cycle}/DataFiles/{demo}.xpt')
        bod = pd.read_sas(f'{BASE_URL}/{cycle}/DataFiles/{bmx}.xpt')
        frames.append(
            dem[['SEQN', 'RIAGENDR', 'RIDAGEYR', 'RIDEXPRG']]
            .merge(bod[['SEQN', 'BMXHT']], on='SEQN')
        )
    return pd.concat(frames, ignore_index=True)


def pre_process(raw):
    """Adults with a recorded height, excluding pregnant respondents."""
    adults = raw[(raw['RIDAGEYR'] >= MIN_AGE)
                 & raw['BMXHT'].notna()
                 & (raw['RIDEXPRG'] != PREGNANT)]
    male = adults[adults['RIAGENDR'] == MALE]['BMXHT']
    female = adults[adults['RIAGENDR'] == FEMALE]['BMXHT']
    return pd.DataFrame({
        'sex': ['male'] * len(male) + ['female'] * len(female),
        'height_cm': list(male) + list(female),
    })


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == ['sex', 'height_cm']
    assert not df.isnull().values.any()
    counts = df['sex'].value_counts()
    assert counts['male'] == 5092, f'male count changed: {counts["male"]}'
    assert counts['female'] == 5386, f'female count changed: {counts["female"]}'
    assert df['height_cm'].between(100, 230).all()


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} rows')


if __name__ == '__main__':
    run()
