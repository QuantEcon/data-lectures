#!/usr/bin/env python3
"""
Builder for lectures/hansen_singleton_1983_data.csv.

Constructs the monthly series the `hansen_singleton_1983` lecture estimates on
-- gross real market return, gross consumption growth, gross consumption
inflation, per-capita real nondurables consumption, and gross real T-bill
return -- from FRED and the Ken French data library, over the same
1959:2-1978:12 sample as the companion 1982 lecture.

The construction is the companion builder's, plus the T-bill leg: the market
return is Ken French `Mkt-RF + RF` standing in for CRSP's value-weighted NYSE
return, the T-bill return is `RF` alone, consumption is FRED's real nondurables
index per head of the 16+ civilian noninstitutional population, and both
nominal returns are deflated by month-over-month gross inflation of the
nondurables price deflator. This file's `gross_real_return` and
`gross_cons_growth` columns are bitwise identical to
`hansen_singleton_1982_data.csv` on the same index -- that file is a strict
subset of this one, kept separate because the two lectures are separate.

Migrated from QuantEcon/lecture-python.myst, where it lived beside its output
at lectures/_static/lecture_specific/hansen_singleton_1983/make_data.py. Both
hansen builders were named make_data.py there and collide in this flat tree,
so each takes its dataset's stem per the naming rule in AGENTS.md. The write
target moved to lectures/, and a validate() stage was added; the arithmetic is
unchanged, and the run below reproduces the migrated bytes exactly.

Stages: fetch -> pre-process -> validate -> write.

Requires only the standard library plus pandas.
"""
import io
import os
import urllib.request
import zipfile

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

FRED_CODES = {
    "population_16plus": "CNP16OV",
    "cons_nd_real_index": "DNDGRA3M086SBEA",
    "cons_nd_price_index": "DNDGRG3M086SBEA",
}
START = "1959-02-01"
END = "1978-12-01"

OUT_FILE = 'hansen_singleton_1983_data.csv'

COLUMNS = [
    "gross_real_return",
    "gross_cons_growth",
    "gross_inflation_cons",
    "consumption_per_capita",
    "gross_real_tbill",
]

# 1959-02 to 1978-12 inclusive, monthly, no gaps. Exact by design: the sample
# is the paper's and does not grow.
N_MONTHS = 239
FIRST_MONTH = pd.Timestamp("1959-02-28")
LAST_MONTH = pd.Timestamp("1978-12-31")


def read_fred(codes, start, end):
    """Download FRED series as a date-indexed DataFrame (columns = codes)."""
    base = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    columns = []
    for code in codes:
        url = f"{base}?id={code}&cosd={start:%Y-%m-%d}&coed={end:%Y-%m-%d}"
        columns.append(
            pd.read_csv(url, index_col=0, parse_dates=True, na_values="."))
    fred = pd.concat(columns, axis=1).astype("float64")
    fred.index.name = "DATE"
    return fred


def read_famafrench_factors(start, end):
    """Download the monthly Fama-French research factors (percent)."""
    url = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
           "F-F_Research_Data_Factors_CSV.zip")
    with urllib.request.urlopen(url) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read(archive.namelist()[0]).decode("utf-8")

    # Preamble, then a monthly table (rows keyed by YYYYMM), then an annual
    # table (rows keyed by YYYY). Keep the contiguous monthly block.
    records = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split(",")]
        key = cells[0]
        if len(key) == 6 and key.isdigit():
            records.append([key] + [float(x) for x in cells[1:5]])
        elif records:
            break
    factors = pd.DataFrame(
        records, columns=["date", "Mkt-RF", "SMB", "HML", "RF"])
    factors.index = pd.PeriodIndex(
        pd.to_datetime(factors["date"], format="%Y%m"), freq="M")
    factors = factors.drop(columns="date")
    window = ((factors.index >= pd.Period(start, "M"))
              & (factors.index <= pd.Period(end, "M")))
    return factors.loc[window]


def to_month_end(index):
    return pd.PeriodIndex(pd.DatetimeIndex(index), freq="M").to_timestamp("M")


def sample_window(start=START, end=END):
    """Fetch and sample bounds. One extra prior month builds the first growth
    rate, which is why the fetch window starts before the sample."""
    start_period = pd.Timestamp(start).to_period("M")
    end_period = pd.Timestamp(end).to_period("M")
    return {
        "fetch_start": (start_period - 1).to_timestamp(how="start"),
        "fetch_end": end_period.to_timestamp("M"),
        "sample_start": start_period.to_timestamp("M"),
        "sample_end": end_period.to_timestamp("M"),
    }


def fetch(start=START, end=END):
    window = sample_window(start, end)
    fred = read_fred(list(FRED_CODES.values()),
                     window["fetch_start"], window["fetch_end"])
    ff = read_famafrench_factors(window["fetch_start"], window["fetch_end"])
    return fred, ff


def pre_process(raw, start=START, end=END):
    fred, ff = raw
    window = sample_window(start, end)

    fred = fred.rename(columns={v: k for k, v in FRED_CODES.items()})
    fred.index = to_month_end(fred.index)
    fred["cons_real_level"] = fred["cons_nd_real_index"]
    fred["cons_price_index"] = fred["cons_nd_price_index"]
    fred["consumption_per_capita"] = (
        fred["cons_real_level"] / fred["population_16plus"])
    fred["gross_cons_growth"] = (
        fred["consumption_per_capita"]
        / fred["consumption_per_capita"].shift(1))
    fred["gross_inflation_cons"] = (
        fred["cons_price_index"] / fred["cons_price_index"].shift(1))

    ff = ff.copy()
    ff.columns = [str(col).strip() for col in ff.columns]
    if ("Mkt-RF" not in ff.columns) or ("RF" not in ff.columns):
        raise KeyError(
            "Fama-French data missing required columns: 'Mkt-RF' and 'RF'.")
    # Mkt-RF and RF are reported in percent per month.
    ff["gross_nom_return"] = 1.0 + (ff["Mkt-RF"] + ff["RF"]) / 100.0
    ff["gross_nom_tbill"] = 1.0 + ff["RF"] / 100.0
    ff.index = ff.index.to_timestamp(how="end")
    ff.index = to_month_end(ff.index)
    market = ff[["gross_nom_return", "gross_nom_tbill"]]

    out = fred.join(market, how="inner")
    out["gross_real_return"] = (
        out["gross_nom_return"] / out["gross_inflation_cons"])
    out["gross_real_tbill"] = (
        out["gross_nom_tbill"] / out["gross_inflation_cons"])
    out = out.loc[window["sample_start"]:window["sample_end"]].dropna()

    frame = out[COLUMNS].copy()
    frame.index.name = "date"
    return frame


def validate(frame):
    """Refuse to write anything that is not the shape we expect."""
    assert list(frame.columns) == COLUMNS
    assert frame.index.name == "date"
    assert (frame.dtypes == "float64").all()
    assert not frame.isnull().values.any()

    # The sample is the paper's, frozen. A short fetch -- an upstream outage
    # part-way through, or a truncated Ken French block -- fails here rather
    # than silently publishing a shorter series.
    assert len(frame) == N_MONTHS, f'expected {N_MONTHS} months, got {len(frame)}'
    assert frame.index[0] == FIRST_MONTH
    assert frame.index[-1] == LAST_MONTH
    assert frame.index.is_monotonic_increasing
    # Month-end stamps on an unbroken monthly grid: 28-31 days apart, always.
    gaps = frame.index.to_series().diff().dropna().dt.days
    assert gaps.between(28, 31).all(), 'index is not an unbroken monthly grid'

    # Four of the five series are GROSS -- ratios near 1, not percentages and
    # not net returns. A units change upstream would pass every structural
    # check above and quietly rescale every figure in the lecture. Bands are
    # wide relative to the observed 1959-1978 spread (returns 0.87-1.16, growth
    # 0.97-1.03, inflation 1.00-1.02, T-bill 0.98-1.01).
    assert frame["gross_real_return"].between(0.5, 1.5).all(), \
        'gross_real_return is not a gross monthly ratio'
    assert frame["gross_cons_growth"].between(0.9, 1.1).all(), \
        'gross_cons_growth is not a gross monthly ratio'
    assert frame["gross_inflation_cons"].between(0.95, 1.05).all(), \
        'gross_inflation_cons is not a gross monthly ratio'
    assert frame["gross_real_tbill"].between(0.95, 1.05).all(), \
        'gross_real_tbill is not a gross monthly ratio'

    # The one LEVEL series, and the one whose units are a ratio of two FRED
    # index bases rather than a rate. It has no natural scale, so it is pinned
    # by its observed order of magnitude (2.1e-4 to 2.7e-4): a rebased FRED
    # index or a population series in thousands rather than units would shift
    # it by orders of magnitude and fail here.
    assert frame["consumption_per_capita"].between(1e-4, 1e-3).all(), \
        'consumption_per_capita is off its expected order of magnitude'

    # The two real returns are built from different Ken French columns and
    # share a deflator. Asserted on the MEAN, not month by month: the market
    # leg beats the T-bill leg in only 54% of months, so a per-month or
    # majority test would sit a few revisions away from failing for no real
    # reason. A positive average excess return over twenty years is the robust
    # form of the same economics.
    excess = frame["gross_real_return"] - frame["gross_real_tbill"]
    assert excess.mean() > 0, 'average excess return over the T-bill is not positive'
    # And they must be distinct series. If the T-bill leg silently picks up the
    # market column -- the natural failure of a mis-joined Ken French frame --
    # every band above still passes and the equity premium quietly vanishes.
    assert not frame["gross_real_return"].equals(frame["gross_real_tbill"]), \
        'the market and T-bill legs are identical'


def run():
    frame = pre_process(fetch())
    validate(frame)
    frame.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE))
    print(f'wrote {OUT_FILE}: {frame.shape[0]} rows x {frame.shape[1]} cols '
          f'({frame.index.min().date()} .. {frame.index.max().date()})')


if __name__ == '__main__':
    run()
