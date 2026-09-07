#!/usr/bin/env python3
"""
Shared, manifest-driven validation: the sidecar's `schema` block is the spec.

Two callers use this unchanged (QuantEcon/data-lectures#119):

  * every dynamic-snapshot builder's validate stage -- the builder calls
    `validate(frame, manifest, previous)` on the frame it is about to write
    and layers its own checks (value bands, grid, per-series revision bounds)
    on top of the summary this returns;
  * the PR-validation workflow (`scripts/validate_datasets.py`), which reads
    every committed CSV with `read_raw()` and runs the same `validate()` with
    no `previous`, so a manifest that drifts from its bytes fails the PR.

What is enforced, and the decision each rule records:

  columns      #120 -- walked IN ORDER; a `name` entry claims one column, a
               `pattern` entry claims the maximal run of CONSECUTIVE columns
               that fullmatch it (Python `re`); at least one; every file
               column must be claimed (exhaustive); a pattern's single
               capture group is the period token `date_range` derives from
  dtype        #122 -- compared by FAMILY: str/string/object are one text
               family, datetime64 matches any unit, a nullable bool read back
               as object with bool values matches `bool`; the declared name
               must be in the canonical vocabulary (checked by the CLI's
               conformance pass, not here)
  known_nulls  #121 -- an integer is an EXACT count
  nulls        #121 -- placement for dynamic snapshots: `along` (rows |
               columns) says which way a series runs; `leading` allows nulls
               before a series' first observation; `ended` lists series that
               stopped (nulls after their last observation); `recent` allows
               nulls in the newest N periods of a live series; `inner` lists
               accepted holes per series, as periods or {sparse_until: P}.
               A null anywhere else fails
  row_count_floor, date_range.start (and .end for non-dynamic files)
  overlap      against `previous` when given: a series may not disappear and
               a populated cell may not go empty; revisions are MEASURED and
               returned (cells_revised, max_abs_change, by series) for the
               builder to bound -- never asserted equal

The frame is the RAW table as written: no index column set, periods as a
column (`read_raw` does this; a builder passes `frame.reset_index()`).
Period labels are compared as text -- YAML hands back `datetime.date` objects
for date-shaped scalars, the same trap scripts/snapshots.py guards against.
"""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd


class ValidationError(Exception):
    """The data broke the published contract -- exit code 2 in a builder."""


def _check(condition, message):
    if not condition:
        raise ValidationError(message)


# ---------------------------------------------------------------------------
# dtype families (#122)
# ---------------------------------------------------------------------------

CANONICAL_DTYPES = {'str', 'float64', 'int64', 'bool', 'datetime64',
                    # storage types a non-CSV format genuinely carries
                    'float32', 'int32', 'int16', 'int8'}

_FAMILY = {
    'str': 'text', 'string': 'text', 'object': 'text',
    'float64': 'float', 'float32': 'float', 'float16': 'float', 'float': 'float',
    'int64': 'int', 'int32': 'int', 'int16': 'int', 'int8': 'int', 'int': 'int',
    'Int64': 'int', 'Int32': 'int',
    'bool': 'bool', 'boolean': 'bool',
}


def family(dtype) -> str:
    s = str(dtype)
    if s.startswith('datetime64'):
        return 'datetime'
    return _FAMILY.get(s, s)


def dtype_matches(series: pd.Series, declared: str) -> bool:
    actual, want = family(series.dtype), family(declared)
    if actual == want:
        return True
    # An all-null column gives pandas nothing to infer from (it reports
    # float64); the declaration cannot be checked against the bytes, and the
    # exact known_nulls count is what guards the column instead.
    if series.isnull().all():
        return True
    # pandas 3 reads text as `str`, pandas 2 as `object`: one family (above).
    # A bool column with nulls comes back as object holding bools + NaN.
    if want == 'bool' and actual == 'text':
        vals = series.dropna()
        return len(vals) == 0 or all(isinstance(v, (bool,)) or v in (True, False) for v in vals)
    # An integer column with nulls is read as float; accept when every value
    # is whole -- the declaration describes the bytes, not pandas' promotion.
    if want == 'int' and actual == 'float':
        vals = series.dropna()
        return len(vals) == 0 or bool((vals == vals.round()).all())
    return False


# ---------------------------------------------------------------------------
# reading the raw file the way the manifest describes it
# ---------------------------------------------------------------------------

def datetime_columns(schema: dict) -> list[str]:
    return [c['name'] for c in schema.get('columns') or []
            if 'name' in c and str(c.get('dtype', '')).startswith('datetime64')]


def read_raw(path, manifest: dict) -> pd.DataFrame:
    """Read a CSV as written, honouring `delimiter` and parsing the columns the
    manifest declares `datetime64`. No index column: the manifest describes
    the bytes on disk, not the frame a particular lecture builds."""
    schema = manifest.get('schema') or {}
    fmt = schema.get('format')
    if fmt != 'csv':
        raise NotImplementedError(f'read_raw handles csv only, not {fmt!r}')
    sep = schema.get('delimiter') or manifest.get('delimiter') or ','
    dates = datetime_columns(schema)
    return pd.read_csv(path, sep=sep, parse_dates=dates or False)


# ---------------------------------------------------------------------------
# columns (#120)
# ---------------------------------------------------------------------------

def match_columns(actual: list[str], entries: list[dict]) -> list[tuple[dict, list[str]]]:
    """Walk the manifest's `columns` in order against the file's columns.
    Returns [(entry, [claimed columns...]), ...]; raises on any mismatch."""
    # An empty header cell (a pandas index written without a name) comes back
    # as `Unnamed: k`; manifests declare it as name: "" (or, older ones, as
    # the pandas label itself). Compare a normalised form, keep the real label.
    def _norm(c):
        return '' if re.fullmatch(r'Unnamed: \d+', str(c)) else str(c)
    matches, i, n = [], 0, len(actual)
    for k, entry in enumerate(entries):
        if 'name' in entry and 'pattern' in entry:
            raise ValidationError(f'columns[{k}] carries both name and pattern')
        if 'name' in entry:
            _check(i < n, f'column {entry["name"]!r} missing: file ended after {actual[:i][-3:]}')
            _check(_norm(actual[i]) == _norm(entry['name']),
                   f'column {i} is {actual[i]!r}, expected {entry["name"]!r}')
            matches.append((entry, [actual[i]])); i += 1
        elif 'pattern' in entry:
            rx = re.compile(entry['pattern'])
            run = []
            while i < n and rx.fullmatch(str(actual[i])):
                run.append(actual[i]); i += 1
            _check(run, f'pattern {entry["pattern"]!r} matched no column at position {i} '
                        f'(next is {actual[i]!r})' if i < n else
                        f'pattern {entry["pattern"]!r} matched no column: wide part missing')
            matches.append((entry, run))
        else:
            raise ValidationError(f'columns[{k}] has neither name nor pattern')
    _check(i == n, f'unexpected column(s) not claimed by any entry: {actual[i:i + 5]}')
    return matches


def _period_from(pattern: str, label: str):
    m = re.fullmatch(pattern, str(label))
    if m and m.groups():
        tok = m.group(1)
        return int(tok) if tok.isdigit() else tok
    return None


def _label(x) -> str:
    """Period labels compared as text; dates normalised to ISO."""
    if isinstance(x, (pd.Timestamp, dt.datetime, dt.date)):
        return pd.Timestamp(x).date().isoformat()
    return str(x)


# ---------------------------------------------------------------------------
# nulls (#121)
# ---------------------------------------------------------------------------

def _series_view(frame: pd.DataFrame, schema: dict, matches) -> tuple[pd.DataFrame, str]:
    """Return (table, along): a frame whose ROWS are periods and COLUMNS are
    series, whichever way the file is laid out, with period labels as text."""
    nulls = schema.get('nulls') or {}
    along = nulls.get('along')
    if along is None:
        along = 'columns' if any('pattern' in e for e, _ in matches) else 'rows'
    if along == 'columns':
        pattern_entries = [(e, cols) for e, cols in matches if 'pattern' in e]
        _check(len(pattern_entries) == 1, 'along: columns needs exactly one pattern entry')
        period_cols = pattern_entries[0][1]
        label_col = matches[0][1][0]           # the first named column labels the series
        table = frame.set_index(label_col)[period_cols].T
        table.index = [_label(c) for c in table.index]
        return table, along
    dates = datetime_columns(schema)
    if dates:
        table = frame.set_index(dates[0])
        table.index = [_label(x) for x in table.index]
    else:
        table = frame.copy()
        table.index = [str(i) for i in table.index]
    return table, along


def check_known_nulls(frame: pd.DataFrame, schema: dict, dynamic: bool = False):
    known = schema.get('known_nulls') or {}
    if not dynamic:
        # A frozen file declares every nulled column; one it does not declare
        # must have none (the template's `known.get(col, 0)` rule, #121).
        for col in frame.columns:
            if col not in known:
                have = int(frame[col].isnull().sum())
                _check(have == 0, f'{col}: {have} nulls but not declared under known_nulls')
    for col, n in known.items():
        _check(col in frame.columns, f'known_nulls names {col!r}, not a column')
        _check(isinstance(n, int) and not isinstance(n, bool),
               f'known_nulls[{col!r}] must be an integer (exact count), got {n!r}')
        have = int(frame[col].isnull().sum())
        _check(have == n, f'{col}: {have} nulls, manifest says exactly {n}')
    return known


def check_placement(frame: pd.DataFrame, schema: dict, matches):
    rule = schema.get('nulls')
    if not rule:
        return
    table, along = _series_view(frame, schema, matches)
    periods = list(table.index)
    leading_ok = bool(rule.get('leading', False))
    recent = int(rule.get('recent', 0) or 0)
    ended = set(map(str, rule.get('ended') or []))
    inner = rule.get('inner') or {}
    recent_set = set(periods[-recent:]) if recent else set()
    for series in table.columns:
        s = table[series]
        if not s.isnull().any():
            continue
        first, last = s.first_valid_index(), s.last_valid_index()
        _check(first is not None, f'{series}: no observation at all')
        pos = {p: k for k, p in enumerate(periods)}
        holes = inner.get(str(series), inner.get(series, []))
        sparse_until = holes.get('sparse_until') if isinstance(holes, dict) else None
        hole_set = set() if isinstance(holes, dict) else {_label(h) for h in holes}
        for p in periods:
            if not pd.isnull(s[p]):
                continue
            if pos[p] < pos[first]:
                _check(leading_ok, f'{series}: null at {p} before first observation, leading nulls not allowed')
                continue
            if pos[p] > pos[last]:
                _check(str(series) in ended or p in recent_set,
                       f'{series}: null at {p} after its last observation {last}; not in `ended` and not within the newest {recent}')
                continue
            ok = p in hole_set or (sparse_until is not None and p < _label(sparse_until)) or p in recent_set
            _check(ok, f'{series}: hole at {p} inside the series is not declared under nulls.inner')


# ---------------------------------------------------------------------------
# date_range, rows, overlap
# ---------------------------------------------------------------------------

def derive_date_range(frame: pd.DataFrame, schema: dict, matches) -> dict:
    for entry, cols in matches:
        if 'pattern' in entry and re.compile(entry['pattern']).groups == 1:
            toks = [_period_from(entry['pattern'], c) for c in cols]
            return {'start': toks[0], 'end': toks[-1]}
    dates = datetime_columns(schema)
    if dates:
        col = frame[dates[0]].dropna()
        return {'start': _label(col.min()), 'end': _label(col.max())}
    return {'start': None, 'end': None}


def _same_period(spec, derived) -> bool:
    if spec is None or derived is None:
        return True
    a, b = _label(spec), _label(derived)
    return a == b or b.startswith(a) or a.startswith(b)


def check_date_range(derived: dict, schema: dict, dynamic: bool):
    spec = schema.get('date_range') or {}
    _check(_same_period(spec.get('start'), derived['start']),
           f'date_range.start is {derived["start"]}, manifest says {spec.get("start")}')
    if not dynamic and spec.get('end') is not None:
        _check(_same_period(spec.get('end'), derived['end']),
               f'date_range.end is {derived["end"]}, manifest says {spec.get("end")}')


def check_rows(frame: pd.DataFrame, schema: dict):
    floor = schema.get('row_count_floor')
    if floor is not None:
        _check(len(frame) >= floor, f'{len(frame)} rows, floor is {floor}')


def overlap(frame: pd.DataFrame, previous: pd.DataFrame, schema: dict, matches) -> dict:
    """Measure the shared window. Asserts only that no series disappeared and
    no populated cell went empty; revisions are returned, not judged."""
    new_t, _ = _series_view(frame, schema, matches)
    prev_matches = match_columns(list(previous.columns), schema.get('columns') or [])
    old_t, _ = _series_view(previous, schema, prev_matches)
    _check(set(old_t.columns) <= set(new_t.columns),
           f'series disappeared: {sorted(set(old_t.columns) - set(new_t.columns))}')
    _check(set(old_t.index) <= set(new_t.index),
           f'period(s) disappeared: {[p for p in old_t.index if p not in set(new_t.index)][:5]}')
    common_p = [p for p in old_t.index if p in new_t.index]
    _check(common_p, 'no period in common with the previous snapshot')
    old = old_t.loc[common_p, old_t.columns]
    new = new_t.loc[common_p, old_t.columns]
    went_empty = old.notnull() & new.isnull()
    _check(not went_empty.any().any(),
           f'a populated cell went empty: {[(c, p) for c in old.columns for p in common_p if went_empty.loc[p, c]][:3]}')
    diff = (old.apply(pd.to_numeric, errors='coerce') - new.apply(pd.to_numeric, errors='coerce')).abs()
    by_series = {str(c): (round(float(diff[c].max()), 6) if diff[c].notnull().any() else 0.0) for c in old.columns}
    return {
        'window': f'{common_p[0]}..{common_p[-1]}',
        'previous_end': old_t.index[-1],
        'cells_total': int(old.notnull().sum().sum()),
        'cells_revised': int((diff > 1e-9).sum().sum()),
        'max_abs_change': round(max(by_series.values()), 6) if by_series else 0.0,
        'max_abs_change_by_series': by_series,
        'new_columns': [p for p in new_t.index if p not in set(old_t.index)],
        'new_series': [str(c) for c in new_t.columns if c not in set(old_t.columns)],
    }


# ---------------------------------------------------------------------------
# the entry point
# ---------------------------------------------------------------------------

def validate(frame: pd.DataFrame, manifest: dict, previous: pd.DataFrame | None = None) -> dict:
    """Enforce the manifest's schema block on a RAW-shaped frame; return the
    run summary a builder writes as --summary-json."""
    schema = manifest.get('schema') or {}
    dynamic = manifest.get('class') == 'dynamic-snapshot'
    _check(len(frame) > 0, 'empty frame')
    matches = match_columns([str(c) for c in frame.columns], schema.get('columns') or [])
    for entry, cols in matches:
        want = entry.get('dtype')
        if want is None:
            continue
        for c in cols:
            _check(dtype_matches(frame[c], want),
                   f'{c}: dtype {frame[c].dtype} is not in the {want!r} family')
    check_rows(frame, schema)
    check_known_nulls(frame, schema, dynamic)
    if dynamic:
        _check('nulls' in schema, 'a dynamic snapshot must declare a `nulls:` placement rule (#121)')
    check_placement(frame, schema, matches)
    derived = derive_date_range(frame, schema, matches)
    check_date_range(derived, schema, dynamic)
    summary = {
        'dataset': manifest.get('filename'),
        'rows': int(frame.shape[0]),
        'columns': int(frame.shape[1]),
        'date_range': derived,
        'overlap': None,
    }
    if previous is not None:
        summary['overlap'] = overlap(frame, previous, schema, matches)
    return summary
