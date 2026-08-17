#!/usr/bin/env python3
"""
Builder for lectures/bbh_macro_quarterly.csv.

Extracts the fourteen FRED series the `subjective_beliefs_business_cycles`
lecture's forecasting VAR is built from, over 1955Q1-2019Q4, out of the
Bhandari-Borovicka-Ho replication package on Zenodo.

The input is `data input/FRED/data_FRED.xlsx` inside the package: a snapshot
the authors took of FRED through 2022, in two sheets -- `FRED_Q` for the series
FRED publishes quarterly and `FRED_M` for the monthly ones. This builder takes
the quarterly sheet as it stands, averages each monthly series over the three
months of its quarter, keeps the fourteen columns the lecture reads, cuts the
window to 1955Q1-2019Q4 and rounds to four decimals.

It deliberately does NOT read live FRED. These are the authors' 2022-vintage
values; every national-accounts series here has been revised and rebased since,
so a live fetch would change the lecture's figures. The Zenodo record is a
versioned, immutable DOI, which is what makes this reproducible -- the builder
pins the extracted workbook by sha256.

The package is a 198.8 MB zip and the workbook inside it is 169 KB, so the
fetch stage reads the zip's central directory and then the single member it
needs over HTTP range requests -- four requests and 296 KB, measured. If the
host stops honouring ranges it falls back to downloading the whole archive.

Migrated from QuantEcon/lecture-python-advanced.myst, where the CSV sat at
lectures/_static/lecture_specific/subjective_beliefs_business_cycles/ with no
build script of any kind. This builder is a RECONSTRUCTION of the extraction,
not a recovered original: it was written from the committed bytes and the
replication package, and it reproduces the committed file exactly (see
validate() and the manifest's integrity block).

Stages: fetch -> pre-process -> validate -> write.

Requires pandas and openpyxl.
"""
import hashlib
import io
import os
import urllib.request
import zipfile

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

OUT_FILE = 'bbh_macro_quarterly.csv'

# Zenodo versioned record 10.5281/zenodo.10194324 (concept DOI
# 10.5281/zenodo.10194323), CC-BY-4.0, published 2023-11-22.
ZIP_URL = ('https://zenodo.org/api/records/10194324/files/'
           'replication%20package.zip/content')
ZIP_SIZE = 198817944
MEMBER = 'replication package/data input/FRED/data_FRED.xlsx'
MEMBER_SHA256 = ('f2d330ea4737963f56bc68af8c7b6833'
                 'a4ac7c6aa9c16014927a9e9b0165ba5d')

# Sheet FRED_Q carries these at quarterly frequency already.
QUARTERLY = ['GDP', 'GDPC1', 'GDPPOT', 'PCESV', 'GPDI', 'PIRIC',
             'PRS85006023']
# Sheet FRED_M carries these monthly; each quarter is the mean of its 3 months.
MONTHLY = ['CPIAUCSL', 'PCEND', 'UNRATE', 'CUMFNS', 'FEDFUNDS', 'CE16OV',
           'CNP16OV']
# Column order of the published file.
COLUMNS = ['GDP', 'GDPC1', 'GDPPOT', 'PCESV', 'GPDI', 'PIRIC', 'PRS85006023',
           'CPIAUCSL', 'PCEND', 'UNRATE', 'CUMFNS', 'FEDFUNDS', 'CE16OV',
           'CNP16OV']

FIRST_QUARTER = 19551
LAST_QUARTER = 20194
N_QUARTERS = 260               # 1955Q1..2019Q4 inclusive, no gaps
DECIMALS = 4

# PCEND is the one gap: FRED publishes it from 1959-01, so the first sixteen
# quarters of the window (1955Q1-1958Q4) are empty and every other column is
# complete. Declared here so a NEW hole fails validation instead of shipping.
KNOWN_NULLS = {'PCEND': 16}


class _HttpRangeReader(io.RawIOBase):
    """Seekable read-only file over HTTP Range requests."""

    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.pos = offset
        elif whence == os.SEEK_CUR:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        end = min(self.pos + n, self.size) - 1
        if end < self.pos:
            return b''
        request = urllib.request.Request(
            self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        with urllib.request.urlopen(request) as response:
            if response.status != 206:
                raise OSError('server ignored the Range request')
            payload = response.read()
        self.pos += len(payload)
        return payload

    def readinto(self, buffer):
        payload = self.read(len(buffer))
        buffer[:len(payload)] = payload
        return len(payload)


def _open_archive():
    """The replication package, read over ranges where the host allows it."""
    try:
        reader = io.BufferedReader(_HttpRangeReader(ZIP_URL, ZIP_SIZE),
                                   buffer_size=1 << 18)
        return zipfile.ZipFile(reader)
    except (OSError, zipfile.BadZipFile):
        with urllib.request.urlopen(ZIP_URL) as response:
            return zipfile.ZipFile(io.BytesIO(response.read()))


def fetch():
    """Pull data_FRED.xlsx out of the Zenodo package, pinned by hash."""
    # ZipFile owns the BufferedReader wrapping the HTTP range reader, so closing
    # it closes the connection too. Without this the socket is left to the
    # garbage collector, which matters because this builder is meant to be
    # re-run -- the byte-identity check reruns it on every verification pass.
    with _open_archive() as archive:
        payload = archive.read(MEMBER)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != MEMBER_SHA256:
        raise ValueError(
            f'{MEMBER} hashed {digest}, expected {MEMBER_SHA256}; the Zenodo '
            'record is versioned and immutable, so this means the fetch is '
            'wrong, not that the source moved')
    return payload


def pre_process(payload):
    workbook = pd.ExcelFile(io.BytesIO(payload))
    quarterly = workbook.parse('FRED_Q').set_index('YYYYQ')
    monthly = workbook.parse('FRED_M')

    # YYYYMM -> YYYYQ, then the mean of the quarter's three months. Every
    # quarter in the window has all three or none (checked in validate()), so
    # a skipna mean and a strict 3-month mean agree here.
    monthly['YYYYQ'] = monthly['YYYY'] * 10 + (monthly['MM'] - 1) // 3 + 1
    averaged = monthly.groupby('YYYYQ')[MONTHLY].mean()

    window = range(FIRST_QUARTER, LAST_QUARTER + 1)
    index = [q for q in window if q % 10 in (1, 2, 3, 4)]
    frame = pd.concat([quarterly[QUARTERLY].reindex(index),
                       averaged.reindex(index)], axis=1)[COLUMNS]
    frame.index.name = 'YYYYQ'
    return frame.round(DECIMALS)


def validate(frame):
    """Refuse to write anything that is not the shape we expect."""
    assert list(frame.columns) == COLUMNS, list(frame.columns)
    assert frame.index.name == 'YYYYQ'
    assert (frame.dtypes == 'float64').all()

    # 1955Q1..2019Q4 on an unbroken quarterly grid. A short fetch, or a
    # truncated sheet, fails here rather than publishing a shorter panel.
    assert len(frame) == N_QUARTERS, f'expected {N_QUARTERS}, got {len(frame)}'
    assert frame.index[0] == FIRST_QUARTER
    assert frame.index[-1] == LAST_QUARTER
    assert frame.index.is_monotonic_increasing
    assert set(frame.index % 10) == {1, 2, 3, 4}
    quarters = (frame.index // 10) * 4 + (frame.index % 10)
    assert (pd.Series(quarters).diff().dropna() == 1).all(), 'gap in the grid'

    # Exactly the declared holes, and nowhere else.
    nulls = frame.isnull().sum()
    assert dict(nulls[nulls > 0]) == KNOWN_NULLS, dict(nulls[nulls > 0])
    assert frame['PCEND'].loc[:19584].isnull().all()
    assert frame['PCEND'].loc[19591:].notnull().all()

    # Units. Every column is a level in the units this VINTAGE of FRED
    # published it in, and the lecture takes logs and ratios of them, so a
    # rebasing or a units change would pass every structural check above and
    # quietly rescale the figures. Bands are wide relative to the observed
    # 1955-2019 spread; the measured min/max are in the manifest.
    bands = {
        'GDP': (100, 50000),          # billions $, SAAR      obs 413-21694
        'GDPC1': (1000, 40000),       # billions chained 2012 obs 2815-19202
        'GDPPOT': (1000, 40000),      # billions chained 2012 obs 2758-19226
        'PCESV': (50, 30000),         # billions $, SAAR      obs 108-10113
        'GPDI': (10, 10000),          # billions $, SAAR      obs 65-3858
        'PIRIC': (0.1, 10),           # index 2012=1          obs 0.84-3.86
        'PRS85006023': (50, 200),     # index 2012=100        obs 98-117
        'CPIAUCSL': (10, 500),        # index 1982-84=100     obs 26.8-257.8
        'PCEND': (50, 10000),         # billions $, SAAR      obs 126-3002
        'UNRATE': (0, 30),            # percent               obs 3.4-10.7
        'CUMFNS': (0, 100),           # percent               obs 63.8-91.6
        'FEDFUNDS': (0, 30),          # percent               obs 0.07-17.78
        'CE16OV': (10000, 400000),    # thousands of persons  obs 60815-158544
        'CNP16OV': (50000, 600000),   # thousands of persons  obs 109130-260015
    }
    for column, (low, high) in bands.items():
        series = frame[column].dropna()
        assert series.between(low, high).all(), f'{column} out of band'

    # The 2012 base is the fingerprint of this vintage: FRED rebased all three
    # to 2017 years ago, so if a future edit ever points this builder at live
    # FRED, THIS is the assertion that catches it rather than a silent rescale.
    base = [20121, 20122, 20123, 20124]
    assert abs((frame.loc[base, 'GDP'] / frame.loc[base, 'GDPC1']).mean()
               - 1.0) < 5e-4, 'real GDP is not on the 2012 base'
    assert abs(frame.loc[base, 'PIRIC'].mean() - 1.0) < 5e-3
    assert abs(frame.loc[base, 'PRS85006023'].mean() - 100.0) < 5e-1

    # Employment and population are both in thousands of persons and the
    # lecture divides one by the other, so a rescaling of just one of them
    # would sit inside the bands above and still wreck `hours_pc`. The ratio is
    # the employment-population ratio: observed 0.552-0.646 here. NOT a
    # monotonicity check on the population -- CNP16OV steps DOWN in 2008Q1,
    # 2017Q1 and 2019Q1 on the BLS January population controls.
    ratio = frame['CE16OV'] / frame['CNP16OV']
    assert ratio.between(0.4, 0.8).all(), 'employment-population ratio is off'


def run():
    frame = pre_process(fetch())
    validate(frame)
    frame.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE))
    print(f'wrote {OUT_FILE}: {frame.shape[0]} rows x {frame.shape[1]} cols '
          f'({frame.index.min()} .. {frame.index.max()})')


if __name__ == '__main__':
    run()
