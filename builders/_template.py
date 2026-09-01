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

Requires pandas plus whatever the source needs (add it to requirements.txt).
"""
import argparse
import datetime as dt
import json
import os
import sys

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')
PROVENANCE_DIR = os.path.join(REPO_ROOT, 'provenance')

OUT_FILE = '<stem>.csv'          # lectures/<stem>.csv -- the manifest's filename
MAX_REVISION = None              # overlap bound in the data's own units; measure first
MAX_STALENESS = None             # newest observation must be at least this recent


class ValidationError(Exception):
    """The fetched data broke the published contract -- exit code 2."""


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
    """Assert the contract the manifest's schema block promises; return the
    run summary. Every failure is a ValidationError with a message a human
    can act on from the canary issue."""
    _check(len(frame) > 0, 'empty frame')
    # columns / dtypes / known_nulls / units / recency ...
    summary = {
        'dataset': OUT_FILE,
        'builder': os.path.relpath(os.path.abspath(__file__), REPO_ROOT),
        'rows': int(frame.shape[0]),
        'columns': int(frame.shape[1]),
        'date_range': {'start': None, 'end': None},
        'overlap': None,
    }
    if previous is not None:
        # compare the shared window; report and BOUND revisions, never assert equality
        raise NotImplementedError
    return summary


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
