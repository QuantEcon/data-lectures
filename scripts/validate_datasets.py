#!/usr/bin/env python3
"""
PR validation (PLAN Phase 5; QuantEcon/data-lectures#119): every manifest
conforms to manifest-schema.yml's executable rules, and every CSV's committed
bytes satisfy its own schema block, via the same builders/_validate.py the
dynamic builders run.

  python scripts/validate_datasets.py             # everything under lectures/
  python scripts/validate_datasets.py lectures/gdp_growth_annual.csv.yml ...
  python scripts/validate_datasets.py --builders   # each dynamic builder's own
                                                  # validate() on the committed bytes

Two passes per manifest:

  conformance (all formats)  class in the enum; every column entry has name
                             XOR pattern; a pattern compiles and has exactly
                             one capture group; dtype in the canonical set
                             (#122); known_nulls values are integers, never a
                             {max: N} ceiling (#121); a dynamic snapshot has
                             a `nulls:` block with known keys; known_nulls_total
                             appears only inside a `header: null` sheet entry
  bytes (csv only)           read_raw() + validate() with no previous vintage

Formats other than csv get the conformance pass only and say so -- reading
xlsx/dta/npy/json ranges the way each lecture does is not built yet.

Exit 1 if anything fails; every failure is a ::error annotation naming the
manifest, so it reads in the PR's checks tab.
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
LECTURES = REPO / 'lectures'
sys.path.insert(0, str(REPO / 'builders'))
from _validate import CANONICAL_DTYPES, ValidationError, read_raw, validate  # noqa: E402

CLASSES = {'verbatim', 'constructed', 'dynamic-snapshot'}
NULLS_KEYS = {'along', 'leading', 'recent', 'ended', 'inner'}


def conformance(m: dict, path: pathlib.Path) -> list[str]:
    errs = []
    if m.get('class') not in CLASSES:
        errs.append(f'class {m.get("class")!r} not in {sorted(CLASSES)}')
    if m.get('filename') != path.name[:-4]:
        errs.append(f'filename {m.get("filename")!r} does not match sidecar name')
    schema = m.get('schema') or {}

    def check_columns(cols, where):
        for k, c in enumerate(cols or []):
            has_name, has_pat = 'name' in c, 'pattern' in c
            if has_name == has_pat and 'index' not in c:
                errs.append(f'{where}[{k}]: needs exactly one of name / pattern')
            if has_pat:
                try:
                    rx = re.compile(c['pattern'])
                    if rx.groups != 1:
                        errs.append(f'{where}[{k}]: pattern {c["pattern"]!r} must have exactly one capture group (#120)')
                except re.error as e:
                    errs.append(f'{where}[{k}]: pattern does not compile: {e}')
            d = c.get('dtype')
            if d is not None and str(d) not in CANONICAL_DTYPES:
                errs.append(f'{where}[{k}] ({c.get("name") or c.get("pattern")}): dtype {d!r} not canonical (#122: {sorted(CANONICAL_DTYPES)})')

    check_columns(schema.get('columns'), 'schema.columns')
    for t in schema.get('tables') or []:
        check_columns(t.get('columns'), f'schema.tables[{t.get("name")}].columns')
    for k, s in enumerate(schema.get('sheets') or []):
        check_columns(s.get('columns'), f'schema.sheets[{k}].columns')
        if 'known_nulls_total' in s and (s.get('read_as') or {}).get('header', 0) is not None:
            errs.append(f'schema.sheets[{k}]: known_nulls_total is legal only with read_as.header: null (#121)')
    if 'known_nulls_total' in schema:
        errs.append('schema.known_nulls_total: retired for named columns -- use known_nulls (exact) and nulls (placement) (#121)')
    for col, n in (schema.get('known_nulls') or {}).items():
        if not isinstance(n, int) or isinstance(n, bool):
            errs.append(f'known_nulls[{col!r}] = {n!r}: must be an exact integer; there is no ceiling form (#121)')
    if m.get('class') == 'dynamic-snapshot':
        rule = schema.get('nulls')
        if not isinstance(rule, dict):
            errs.append('dynamic-snapshot without a `nulls:` placement block (#121)')
        else:
            bad = set(rule) - NULLS_KEYS
            if bad:
                errs.append(f'nulls: unknown key(s) {sorted(bad)}; allowed {sorted(NULLS_KEYS)}')
            if rule.get('along') not in ('rows', 'columns'):
                errs.append(f'nulls.along must be rows | columns, got {rule.get("along")!r}')
    return errs


def builder_layer() -> int:
    """The builder-layer half: every dynamic snapshot's own validate() on its
    COMMITTED bytes, no network, through the builder's check_committed()
    (#128 -- a builder check that broke under pandas 3 while the shared
    layer stayed green, unseen until a validator dry-ran the builder)."""
    import importlib
    failed = 0
    seen = set()          # a set-writing builder is named by several manifests; run it once
    for path in sorted(LECTURES.glob('*.yml')):
        m = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if m.get('class') != 'dynamic-snapshot' or m.get('builder_status') != 'committed':
            continue
        if m['builder'] in seen:
            continue
        seen.add(m['builder'])
        mod_name = pathlib.Path(m['builder']).stem
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, 'check_committed', None)
            if fn is None:
                raise AttributeError(f'{m["builder"]} has no check_committed() (see builders/_template.py)')
            for f in fn():
                print(f'{"ok  builder layer":70s} {f}  ({m["builder"]})')
        except Exception as e:
            failed += 1
            print(f'::error file={m["builder"]}::{type(e).__name__}: {e}')
            print(f'FAIL {m["filename"]}: builder layer')
    return failed


def main(argv: list[str]) -> int:
    if argv and argv[0] == '--builders':
        n = builder_layer()
        print(f'\nbuilder layer: {"all green" if not n else f"{n} builder(s) failed"}')
        return 1 if n else 0
    # Resolve the arguments: REPO is absolute and relative_to() does not
    # resolve, so a relative path crashed the failure report (#129).
    paths = [pathlib.Path(a).resolve() for a in argv] or sorted(LECTURES.glob('*.yml'))
    failed = 0
    skipped_formats: dict[str, int] = {}
    for path in paths:
        m = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if 'filename' not in m:
            continue
        problems = conformance(m, path)
        fmt = (m.get('schema') or {}).get('format')
        status = 'conformance only'
        if not problems and fmt == 'csv':
            data = LECTURES / m['filename']
            if not data.exists():
                problems.append(f'{m["filename"]} not found beside its manifest')
            else:
                try:
                    s = validate(read_raw(data, m), m)
                    status = f'ok  rows={s["rows"]} cols={s["columns"]} range={s["date_range"]["start"]}..{s["date_range"]["end"]}'
                except ValidationError as e:
                    problems.append(str(e))
                except Exception as e:  # a read failure is a failure of the contract too
                    problems.append(f'{type(e).__name__}: {e}')
        elif not problems:
            skipped_formats[fmt] = skipped_formats.get(fmt, 0) + 1
            status = f'conformance only ({fmt})'
        if problems:
            failed += 1
            for p in problems:
                print(f'::error file={path.relative_to(REPO)}::{p}')
            print(f'FAIL {path.name}: {len(problems)} problem(s)')
        else:
            print(f'{status:70s} {path.name}')
    n = len(paths)
    print(f'\n{n} manifest(s): {n - failed} pass, {failed} fail; bytes-validated formats: csv; '
          f'conformance-only: {skipped_formats}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
