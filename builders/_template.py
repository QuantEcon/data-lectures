#!/usr/bin/env python3
"""
TEMPLATE for a dynamic-snapshot builder -- copy to builders/<stem>.py and
replace every NotImplementedError. Not a builder itself: the leading
underscore keeps it out of any manifest's `builder:` field, and CI asserts
only the paths manifests name.

Distilled from builders/business_cycle.py (the first dynamic snapshot) and
QuantEcon/data-lectures#14. The contract the refresh workflow relies on
(.github/workflows/refresh-snapshots.yml, scripts/snapshots.py):

  stages      fetch -> pre_process -> validate -> write, writing ONLY on a
              validation pass, through a temp file + os.replace(), so a
              failed or interrupted refresh leaves the last-good snapshot
  --out-dir   dry run: write everything to a directory, still validating
              against the committed file in lectures/ (the weekly canary)
  --summary-json
              write the run summary as JSON -- the refresh PR's body and the
              manifest stamp are built from it; keys: dataset, builder, rows,
              columns, date_range{start,end}, overlap{window, previous_end,
              cells_total, cells_revised, max_abs_change, new_columns}|null
  exit codes  0 ok; 1 fetch/other failure (retry); 2 ValidationError (the
              data broke the contract -- a human decides)
  overlap     a TRACKING snapshot is revised by its source; validate() bounds
              the overlap window and reports it rather than asserting
              equality. Measure the source's routine revisions before
              choosing the bound (business_cycle: observed max 1.5 pp,
              bound 5 pp)
  provenance  upstream metadata dumps go to provenance/, never lectures/;
              collapse runs of blank lines so a refresh diff shows content
  manifest    prose in the sidecar must not embed facts a refresh can change
              (an end year, an observed range, a row count) -- those live in
              the fields scripts/snapshots.py stamps, and only there

Requires pandas and PyYAML plus whatever the source needs (add it to requirements.txt).
"""
import argparse
import datetime as dt
import json
import os
import sys

import pandas as pd
import yaml

from _validate import ValidationError, validate as validate_schema

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
PROVENANCE_DIR = os.path.join(REPO_ROOT, 'provenance')

OUT_FILE = '<stem>.csv'          # lectures/<stem>.csv -- the manifest's filename
MAX_REVISION = None              # overlap bound in the data's own units; measure first
MAX_STALENESS = None             # newest observation must be at least this recent


def _check(condition, message):
    if not condition:
        raise ValidationError(message)


def fetch():
    """Pull raw data from the upstream. Network failures surface here (exit 1)."""
    raise NotImplementedError


def pre_process(raw):
    """Pure raw -> published frame. No I/O; absorb upstream renames HERE so
    the published schema never changes under a consumer."""
    raise NotImplementedError


def validate(frame, previous=None):
    """Two layers (QuantEcon/data-lectures#119). The manifest's schema block
    is the spec -- columns and pattern runs, dtype families, exact known_nulls,
    the `nulls:` placement rule, row_count_floor, date_range, and the overlap
    window MEASURED against `previous` -- enforced by builders/_validate.py.
    Add here only what a schema cannot say: value bands, a grid, recency, and
    the revision BOUND. Every failure is a ValidationError with a message a
    human can act on from the canary issue."""
    with open(os.path.join(PUBLISHED_DIR, OUT_FILE + '.yml')) as f:
        manifest = yaml.safe_load(f)
    # pass the RAW shape: the period/label column as a column, not the index
    raw = frame.reset_index() if frame.index.name else frame
    prev_raw = previous.reset_index() if previous is not None and previous.index.name else previous
    shared = validate_schema(raw, manifest, prev_raw)
    # builder-specific: bands / grid / recency ... Two idioms that bit once:
    # call .dropna() BEFORE a band check (pandas 3's stack() keeps NaN, #128),
    # and never compare against a dtype string -- the shared validator already
    # did that by family (#122).
    raise NotImplementedError
    summary = {
        'dataset': OUT_FILE,
        'builder': os.path.relpath(os.path.abspath(__file__), REPO_ROOT),
        'rows': shared['rows'],
        'columns': shared['columns'],
        'date_range': shared['date_range'],
        'overlap': shared['overlap'],
    }
    if previous is not None:
        _check(shared['overlap']['max_abs_change'] <= MAX_REVISION,
               f'revision {shared["overlap"]["max_abs_change"]} exceeds {MAX_REVISION}')
    return summary


def check_committed():
    """Builder-layer validation of the COMMITTED file(s), no network. Called by
    scripts/validate_datasets.py --builders on every PR, under both pandas
    majors, so a builder-specific check that breaks on a pandas change fails
    the PR rather than the next canary. Yield each file validated."""
    frame = pd.read_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index_col=0)
    validate(frame)
    yield OUT_FILE


def _atomic_write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, path)


def run(out_dir=None, summary_json=None):
    data_dir = out_dir or PUBLISHED_DIR
    previous_path = os.path.join(PUBLISHED_DIR, OUT_FILE)
    previous = pd.read_csv(previous_path, index_col=0) if os.path.exists(previous_path) else None

    frame = pre_process(fetch())
    summary = validate(frame, previous)
    if summary_json:
        _atomic_write(summary_json, json.dumps(summary, indent=1) + '\n')

    os.makedirs(data_dir, exist_ok=True)
    _atomic_write(os.path.join(data_dir, OUT_FILE), frame.to_csv())
    print(f'wrote {OUT_FILE}: {frame.shape[0]} rows x {frame.shape[1]} cols -> {data_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out-dir')
    ap.add_argument('--summary-json')
    args = ap.parse_args()
    try:
        run(args.out_dir, args.summary_json)
    except ValidationError as exc:
        print(f'::error::{OUT_FILE}: validation failed -- {exc}', file=sys.stderr)
        sys.exit(2)
