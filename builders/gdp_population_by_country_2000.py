"""
Builder for lectures/gdp_population_by_country_2000.csv.

A smaller teaching extract cut from lectures/test_pwt.csv, for lectures that
want a running example with no unused columns. It keeps country, POP, tcgdp, cc
and cg, and drops the Uruguay row. Values are copied as text, so every number
matches test_pwt.csv digit for digit.

The input is a file in this checkout, not a network read: test_pwt.csv is itself
a frozen extract whose upstream vintage is unestablished, so there is nothing
further upstream to fetch.

Stages: fetch -> pre-process -> validate -> write.
"""

import io
import os

import pandas as pd
import yaml

from _validate import validate as validate_schema

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

IN_FILE = 'test_pwt.csv'
OUT_FILE = 'gdp_population_by_country_2000.csv'

COLUMNS = ['country', 'POP', 'tcgdp', 'cc', 'cg']
DROPPED_COUNTRY = 'Uruguay'


def fetch():
    """Read the parent extract as text, so that no number is reformatted."""
    return pd.read_csv(os.path.join(PUBLISHED_DIR, IN_FILE), dtype=str)


def pre_process(raw):
    """Keep the columns the lectures use and drop one country."""
    return raw.loc[raw['country'] != DROPPED_COUNTRY, COLUMNS]


def validate(text):
    """Check the bytes about to be written against the manifest's schema."""
    with open(os.path.join(PUBLISHED_DIR, OUT_FILE + '.yml')) as f:
        manifest = yaml.safe_load(f)
    frame = pd.read_csv(io.StringIO(text))
    validate_schema(frame, manifest)
    assert len(frame) == 7, f'expected 7 rows, got {len(frame)}'
    assert DROPPED_COUNTRY not in set(frame['country'])


def run():
    text = pre_process(fetch()).to_csv(index=False, lineterminator='\n')
    validate(text)
    with open(os.path.join(PUBLISHED_DIR, OUT_FILE), 'w', newline='') as f:
        f.write(text)
    print(f'wrote {OUT_FILE}')


if __name__ == '__main__':
    run()
