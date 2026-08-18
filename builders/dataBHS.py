"""
Builder for lectures/dataBHS.csv.

Converts the Barillas-Hansen-Sargent "Doubts or variability?" (JET, 2009)
MATLAB data file into the CSV the `five_preferences` lecture reads. Three
quarterly US series over 1948Q1-2006Q4: log real per-capita consumption and
two gross real asset returns. The file carries no date column; the sample is
stated in the paper and in the consuming lecture's prose ("1948.I-2006.IV").

This is a value-preserving container conversion and nothing else -- .mat to
.csv, no filtering, no rescaling, no reordering. The published CSV parses back
bit-exactly under pandas' correctly-rounded reader, and -- measured, not
assumed -- the consuming lecture's histogram of consumption growth has
identical counts and bin edges under pandas' DEFAULT parser, so the lecture
needs no float_precision flag.

READS ITS INPUT FROM sources/, WHICH IS THE EXCEPTION, NOT THE RULE.
AGENTS.md permits it only when the input cannot be re-fetched, and this one
cannot: neither author hosts the replication files (tomsargent.com's source
page 404s, larspeterhansen.org lists no code or data for the paper), the
Journal of Economic Theory article carries no data supplement, and a
GitHub-wide code search finds only QuantEcon's own inherited copies of this
blob. Searched with positive controls 2026-08-18 -- see sources/README.md.

Stages: fetch -> pre-process -> validate -> write.
"""

import io
import os

import pandas as pd
from scipy.io import loadmat

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
SOURCES_DIR = os.path.join(REPO_ROOT, 'sources')

SOURCE_FILE = 'dataBHS.mat'

# The .mat holds three bare (236, 1) float64 arrays under these names, in this
# order. The output column order is the input order -- see validate().
COLUMNS = ['c', 'rb', 'rs']

# 1948Q1 to 2006Q4 inclusive, quarterly, no gaps -- 59 years x 4.
N_QUARTERS = 236

# The consuming lecture hardcodes the mean and standard deviation of quarterly
# log consumption growth (five_preferences.md, "Set parameter values"). They
# are moments of THIS vintage, so they double as its fingerprint: a substituted
# or truncated input fails here rather than silently mis-plotting the lecture's
# approximating and worst-case densities against its histogram.
GROWTH_MEAN = 0.004952
GROWTH_STD = 0.005050

OUT_FILE = 'dataBHS.csv'


def fetch():
    return loadmat(os.path.join(SOURCES_DIR, SOURCE_FILE))


def pre_process(raw):
    # Each array is (236, 1); ravel to 1-D so the frame is 236 rows, not 236
    # columns of one element.
    return pd.DataFrame({name: raw[name].ravel() for name in COLUMNS})


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == COLUMNS
    assert len(df) == N_QUARTERS, f'expected {N_QUARTERS} quarters, got {len(df)}'
    assert not df.isnull().values.any()
    assert (df.dtypes == 'float64').all()

    # c is LOG per-capita consumption; rb and rs are GROSS real returns. A
    # vintage stored in levels, percentages or net returns would pass the
    # structural checks above and quietly rescale everything downstream.
    assert df['c'].between(-5.0, -3.0).all(), 'c is not log consumption'
    assert df['rb'].between(0.9, 1.1).all(), 'rb is not a gross return'
    assert df['rs'].between(0.6, 1.4).all(), 'rs is not a gross return'

    # The lecture's hardcoded moments of quarterly log consumption growth,
    # reproduced to their printed precision.
    growth = df['c'].to_numpy()[1:] - df['c'].to_numpy()[:-1]
    assert round(growth.mean(), 6) == GROWTH_MEAN, growth.mean()
    assert round(growth.std(), 6) == GROWTH_STD, growth.std()

    # The conversion contract: the CSV must parse back bit-exactly under the
    # correctly-rounded reader. (pandas' default parser is fast, not correctly
    # rounded -- PLAN-QELD-PACKAGE.md section 4.3 measured 18 of 708 values off
    # by <= 2.1e-16 relative under 'high'. The lecture's histogram is identical
    # either way, which is what lets the lecture keep a plain read_csv.)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    back = pd.read_csv(buffer, float_precision='round_trip')
    for name in COLUMNS:
        assert (back[name].to_numpy() == df[name].to_numpy()).all(), \
            f'{name} does not round-trip bit-exactly'


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} quarters x {len(df.columns)} series')


if __name__ == '__main__':
    run()
