#!/usr/bin/env python3
"""
Builder for lectures/bbh_michigan_monthly.csv.

Rebuilds the monthly Michigan Survey of Consumers aggregates that the
`subjective_beliefs_business_cycles` lecture reads, by extracting three members
from the Bhandari-Borovicka-Ho replication package deposited on Zenodo
(doi:10.5281/zenodo.10194324, CC BY 4.0):

    data input/Michigan/PX1_M.csv      -> px1_mean   (column px1_mean_all)
    data input/Michigan/UMEX_M.csv     -> share_more (column umex_u_all)
                                          share_same (column umex_s_all)
                                          share_less (column umex_f_all)
    data input/FRED/data_FRED.xlsx     -> unrate     (sheet FRED_M, column UNRATE)

QuantEcon's contribution is the extraction: pick five columns out of the 375
those three members carry (273 + 81 + 21), rename them, restrict to the "all
households" demographic cell, window to 1978-01..2020-03, and write a tidy CSV.
No arithmetic is performed -- every value is copied verbatim. It was written
during the wave-C1 migration (2026-08-17) by reverse-engineering the committed
bytes; it did not accompany them into lecture-python-advanced.myst. It
reproduces the committed file byte for byte (sha256 567efe5a...).

Why the deposit and not the live sources: the four Michigan columns are the
*vintage the paper used* (the package's Michigan CSVs were cut 2021-12-17, and
the Surveys of Consumers revise), and the unemployment column matches a 2023
FRED vintage rather than today's -- three months of UNRATE have since been
revised by 0.1pp. A Zenodo DOI deposit is immutable, so it pins both. Refetching
from data.sca.isr.umich.edu and FRED today would silently adopt a new vintage,
which AGENTS.md ("A migration moves bytes; it does not update them") forbids.

Network cost: the deposit is a single 189 MiB zip. This builder HTTP-range-reads
the zip's central directory and then only the three compressed members it needs
(824,944 bytes transferred in total, measured -- each member is read through a
256 KiB buffer, so reads overshoot the ~310 KiB of compressed member bytes),
falling back to a full download if the host stops honouring Range.

Stages: fetch -> pre-process -> validate -> write.

Requires pandas and openpyxl (for the .xlsx member) plus the standard library.
"""
import io
import json
import os
import urllib.request
import zipfile

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

OUT_FILE = 'bbh_michigan_monthly.csv'

ZENODO_RECORD = '10194324'
ZENODO_API = f'https://zenodo.org/api/records/{ZENODO_RECORD}'
# Declared by the Zenodo record on 2026-08-17. Asserted, not trusted: a changed
# deposit is a changed vintage and must fail loudly rather than rebuild quietly.
ZIP_KEY = 'replication package.zip'
ZIP_MD5 = '6e33f9b9e70135cbf3304275d1c5d604'
ZIP_SIZE = 198817944

MEMBER_PX1 = 'replication package/data input/Michigan/PX1_M.csv'
MEMBER_UMEX = 'replication package/data input/Michigan/UMEX_M.csv'
MEMBER_FRED = 'replication package/data input/FRED/data_FRED.xlsx'
FRED_SHEET = 'FRED_M'

# CRC32 of each member as recorded in the deposit's central directory
# (read 2026-08-17). zipfile verifies these on read; asserting them as well
# names the vintage in the source rather than leaving it implicit.
MEMBER_CRC = {
    MEMBER_PX1: 0x9cc4bf83,
    MEMBER_UMEX: 0x8e5b8eb5,
    MEMBER_FRED: 0x615ce461,
}

# source column -> published column. The `_all` suffix is the survey's
# all-households cell; the package also ships the same statistics broken out by
# age, income, education, region and gender, none of which is published here.
COLUMN_MAP = {
    'px1_mean_all': 'px1_mean',    # mean expected price change, next 12 months
    'umex_u_all': 'share_more',    # "more unemployment"  (Michigan table 30)
    'umex_s_all': 'share_same',    # "about the same"
    'umex_f_all': 'share_less',    # "less unemployment"
}
COLUMNS = ['px1_mean', 'share_more', 'share_same', 'share_less', 'unrate']
INDEX_NAME = 'yyyymm'

# The committed window. Exact by design, not a floor with headroom: 197801 is
# where the package's Michigan monthly files begin, and 202003 is where the
# committed extract was cut (the package itself runs to 202110). The lecture
# only reads the first month of each quarter from 198204 to 202001, so this is
# already wider than the lecture needs.
FIRST_MONTH = 197801
LAST_MONTH = 202003
N_MONTHS = 507


def _range_get(url, start, end):
    request = urllib.request.Request(
        url, headers={'Range': f'bytes={start}-{end}'})
    with urllib.request.urlopen(request) as response:
        return response.read(), response.status


class _RemoteZipFile(io.IOBase):
    """Seekable read-only file over HTTP Range requests."""

    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n <= 0 or self.pos >= self.size:
            return b''
        end = min(self.pos + n, self.size) - 1
        payload, status = _range_get(self.url, self.pos, end)
        if status != 206:
            raise OSError('server ignored Range request')
        self.pos += len(payload)
        return payload

    def readinto(self, buffer):
        payload = self.read(len(buffer))
        buffer[:len(payload)] = payload
        return len(payload)


def open_deposit():
    """Return an open ZipFile over the Zenodo deposit, without downloading it
    whole if the host honours Range requests."""
    with urllib.request.urlopen(ZENODO_API) as response:
        record = json.load(response)
    files = {f['key']: f for f in record['files']}
    if ZIP_KEY not in files:
        raise KeyError(f'{ZENODO_API}: no file named {ZIP_KEY!r}')
    entry = files[ZIP_KEY]
    if entry['checksum'] != f'md5:{ZIP_MD5}' or entry['size'] != ZIP_SIZE:
        raise ValueError(
            'Zenodo deposit has changed: expected '
            f'md5:{ZIP_MD5} / {ZIP_SIZE} B, got '
            f"{entry['checksum']} / {entry['size']} B")
    url = entry['links']['self']
    try:
        return zipfile.ZipFile(
            io.BufferedReader(_RemoteZipFile(url, ZIP_SIZE), buffer_size=1 << 18))
    except OSError:
        # Range unsupported: fall back to fetching the whole 189 MiB deposit.
        with urllib.request.urlopen(url) as response:
            payload = response.read()
        return zipfile.ZipFile(io.BytesIO(payload))


def fetch():
    with open_deposit() as deposit:
        for member, crc in MEMBER_CRC.items():
            found = deposit.getinfo(member).CRC
            if found != crc:
                raise ValueError(
                    f'{member}: expected CRC32 0x{crc:08x}, got 0x{found:08x}')
        # ZipFile.read() verifies each member's CRC32 as it decompresses.
        px1 = pd.read_csv(io.BytesIO(deposit.read(MEMBER_PX1)))
        umex = pd.read_csv(io.BytesIO(deposit.read(MEMBER_UMEX)))
        fred = pd.read_excel(io.BytesIO(deposit.read(MEMBER_FRED)),
                             sheet_name=FRED_SHEET)
    return px1, umex, fred


def pre_process(raw):
    px1, umex, fred = raw

    survey = (px1.set_index('yyyymm')[['px1_mean_all']]
              .join(umex.set_index('yyyymm')[
                  ['umex_u_all', 'umex_s_all', 'umex_f_all']], how='inner')
              .rename(columns=COLUMN_MAP))
    unrate = (fred.set_index('YYYYMM')['UNRATE']
              .rename('unrate').rename_axis(INDEX_NAME))

    frame = survey.join(unrate, how='inner')
    frame = frame.loc[FIRST_MONTH:LAST_MONTH, COLUMNS].copy()

    # The three response shares are whole percents in the source and are
    # published as integers; a float column here would change the bytes.
    for column in ['share_more', 'share_same', 'share_less']:
        frame[column] = frame[column].astype('int64')
    frame.index = frame.index.astype('int64')
    frame.index.name = INDEX_NAME
    return frame


def validate(frame):
    """Refuse to write anything that is not the shape we expect."""
    assert list(frame.columns) == COLUMNS, list(frame.columns)
    assert frame.index.name == INDEX_NAME
    assert not frame.isnull().values.any(), 'unexpected nulls'

    # The window is frozen -- a short fetch, a truncated member or an upstream
    # re-cut fails here rather than silently publishing a different series.
    assert len(frame) == N_MONTHS, f'expected {N_MONTHS} rows, got {len(frame)}'
    assert frame.index[0] == FIRST_MONTH
    assert frame.index[-1] == LAST_MONTH
    assert frame.index.is_monotonic_increasing
    assert frame.index.is_unique

    # yyyymm on an unbroken monthly grid: month field always in 1..12, and
    # consecutive stamps always one calendar month apart.
    months = frame.index % 100
    assert months.min() >= 1 and months.max() <= 12, 'bad month field'
    ordinal = (frame.index // 100) * 12 + months
    assert (pd.Series(ordinal).diff().dropna() == 1).all(), \
        'index is not an unbroken monthly grid'

    assert frame['px1_mean'].dtype == 'float64'
    assert frame['unrate'].dtype == 'float64'
    for column in ['share_more', 'share_same', 'share_less']:
        assert frame[column].dtype == 'int64'

    # Units guard. All five columns are percentages or percentage points; a
    # source switching to fractions would pass every structural check above and
    # quietly rescale every figure in the lecture. Bands are wide relative to
    # the observed 1978-2020 spread (px1_mean 1.0-13.8, unrate 3.5-10.8), and
    # the max() floors are what actually catch a divide-by-100 -- a band alone
    # does not, since fractions sit inside it.
    assert frame['px1_mean'].between(-5, 30).all(), \
        'px1_mean is not a percent-per-year inflation expectation'
    assert frame['px1_mean'].max() > 1.0, 'px1_mean looks rescaled to fractions'
    assert frame['unrate'].between(0, 30).all(), \
        'unrate is not a percent unemployment rate'
    assert frame['unrate'].max() > 1.0, 'unrate looks rescaled to fractions'
    for column in ['share_more', 'share_same', 'share_less']:
        assert frame[column].between(0, 100).all(), f'{column} is not a percent'

    # The three shares are the answer distribution net of "don't know", so they
    # sum to at most 100 and never to much less.
    total = frame['share_more'] + frame['share_same'] + frame['share_less']
    assert total.between(85, 100).all(), \
        'response shares do not look like a percent distribution'


def run():
    frame = pre_process(fetch())
    validate(frame)
    frame.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE))
    print(f'wrote {OUT_FILE}: {frame.shape[0]} rows x {frame.shape[1]} cols '
          f'({frame.index[0]} .. {frame.index[-1]})')


if __name__ == '__main__':
    run()
