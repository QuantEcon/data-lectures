"""
Builder for lectures/japan_earthquakes.csv.

Snapshots the USGS earthquake catalog for events of magnitude 5 and above in
the region around Japan, from 2000 to the end of 2024.

The USGS FDSN event service is a live API. Following the rule in AGENTS.md
that lectures read snapshots rather than calling APIs, this builder queries it
once and commits the result.

The extract supports two exercises: whether counts per period look Poisson, and
whether the times between events look exponential. Neither holds, because
aftershocks cluster -- which is the point.

Stages: fetch -> pre-process -> validate -> write.
"""

import os

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

# Region: a box around the Japanese archipelago and its subduction zones.
QUERY = {
    'format': 'csv',
    'starttime': '2000-01-01',
    'endtime': '2024-12-31',
    'minmagnitude': '5',
    'minlatitude': '24',
    'maxlatitude': '46',
    'minlongitude': '122',
    'maxlongitude': '150',
    'orderby': 'time-asc',
}

SOURCE_URL = 'https://earthquake.usgs.gov/fdsnws/event/1/query'

OUT_FILE = 'japan_earthquakes.csv'


def fetch():
    query = '&'.join(f'{k}={v}' for k, v in QUERY.items())
    return pd.read_csv(f'{SOURCE_URL}?{query}')


def pre_process(raw):
    df = pd.DataFrame({
        'time': raw['time'],
        'magnitude': raw['mag'],
        'latitude': raw['latitude'],
        'longitude': raw['longitude'],
        'depth_km': raw['depth'],
    })
    return df.sort_values('time').reset_index(drop=True)


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == ['time', 'magnitude', 'latitude', 'longitude',
                                'depth_km']
    assert not df[['time', 'magnitude']].isnull().values.any()
    assert len(df) > 3000, f'suspiciously few events: {len(df)}'
    assert df['magnitude'].min() >= 5.0
    assert df['latitude'].between(24, 46).all()
    assert df['longitude'].between(122, 150).all()
    assert df['time'].is_monotonic_increasing
    years = pd.to_datetime(df['time'], format='ISO8601').dt.year
    assert years.min() == 2000 and years.max() == 2024


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} events, '
          f'magnitudes {df["magnitude"].min()} to {df["magnitude"].max()}')


if __name__ == '__main__':
    run()
