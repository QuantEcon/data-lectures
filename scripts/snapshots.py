#!/usr/bin/env python3
"""Manifest-driven plumbing for dynamic snapshots (PLAN Phase 5).

The builders do the fetching and validating; this script does everything the
refresh workflow needs to know or write that lives in the manifests:

    list                 every `class: dynamic-snapshot` dataset with a
                         runnable builder, as JSON (the canary matrix)
    due                  the subset whose refresh is due, as JSON (the refresh
                         matrix): cadence elapsed since `retrieved`, or
                         `integrity.upstream.status: diverged`, or never
                         refreshed. `--all` makes every dataset due
    stamp <dataset>      after a builder run, rewrite the sidecar manifest from
      --summary S        the builder's --summary-json: integrity.sha256 of the
                         new bytes, `retrieved`, integrity.upstream (verified,
                         today, the builder, one-line note; the `diverged`
                         delta block is dropped), schema.date_range.end
    pr-body <dataset>    the refresh PR's title (first line) and body, from the
      --summary S        same summary plus the manifest's consumers

`stamp` edits the manifest TEXT, not a parsed-and-re-dumped copy: the sidecars
carry their reasoning as comments, and PyYAML would throw every one of them
away. It finds a key by walking indentation, replaces the key line plus any
continuation lines with a single-line value, and then re-parses the file with
PyYAML to prove the result reads back as intended — a stamp that cannot be
verified fails rather than lands.

Usage from the workflow (.github/workflows/refresh-snapshots.yml):

    python scripts/snapshots.py due
    python builders/<stem>.py --summary-json summary.json
    python scripts/snapshots.py stamp <dataset> --summary summary.json
    python scripts/snapshots.py pr-body <dataset> --summary summary.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
LECTURES = REPO / "lectures"

CADENCE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91, "annual": 365}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def load_manifests() -> dict[str, dict]:
    out = {}
    for path in sorted(LECTURES.glob("*.yml")):
        m = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        out[m.get("filename") or path.name[:-4]] = m
    return out


def snapshots(manifests: dict[str, dict]) -> list[dict]:
    """Every dynamic snapshot with a runnable builder."""
    rows = []
    for fname, m in manifests.items():
        if m.get("class") != "dynamic-snapshot":
            continue
        if m.get("builder_status") != "committed" or not m.get("builder"):
            continue
        rows.append({
            "dataset": fname,
            "stem": pathlib.Path(fname).stem,
            "builder": m["builder"],
            "cadence": m.get("cadence"),
            "retrieved": _iso(m.get("retrieved")),
            "upstream_status": ((m.get("integrity") or {}).get("upstream") or {}).get("status"),
        })
    return rows


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


def is_due(row: dict, today: dt.date) -> tuple[bool, str]:
    if row["upstream_status"] == "diverged":
        return True, "integrity.upstream.status is `diverged` — known to be behind the source"
    if not row["retrieved"]:
        return True, "never refreshed (`retrieved: null`)"
    days = CADENCE_DAYS.get(row["cadence"])
    if days is None:
        return True, f"cadence {row['cadence']!r} is not in {sorted(CADENCE_DAYS)} — treating as due"
    last = dt.date.fromisoformat(row["retrieved"])
    age = (today - last).days
    if age >= days:
        return True, f"cadence `{row['cadence']}` elapsed: last retrieved {last}, {age} days ago"
    return False, f"not due: last retrieved {last}, {age} of {days} days"


# ---------------------------------------------------------------------------
# Text-level manifest editing
# ---------------------------------------------------------------------------

KEY_RE = re.compile(r"^(?P<indent>[ ]*)(?P<key>[A-Za-z_][\w.-]*):(?P<rest>.*)$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _find_key(lines: list[str], path: list[str]) -> tuple[int, int]:
    """(start, end) line span of the key at `path`, including continuation
    lines; end is exclusive. Comment and blank lines inside a block are
    skipped when descending, and a trailing run of them is NOT swallowed into
    the span, so the reasoning above the next key survives an edit."""
    start, stop, depth_indent = 0, len(lines), -1
    for i, key in enumerate(path):
        found = None
        for n in range(start, stop):
            line = lines[n]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            ind = _indent(line)
            if ind <= depth_indent:
                break                                    # left the parent block
            m = KEY_RE.match(line)
            if m and m.group("key") == key and (depth_indent < 0 and ind == 0 or ind > depth_indent):
                if found is None:
                    found = n
                    if i < len(path) - 1:
                        depth_indent = ind
                        start = n + 1
                        # the block ends at the next line at <= this indent
                        stop = next((k for k in range(n + 1, len(lines))
                                     if lines[k].strip() and not lines[k].lstrip().startswith("#")
                                     and _indent(lines[k]) <= ind), len(lines))
                    break
        if found is None:
            raise KeyError(".".join(path))
    key_line = found
    key_indent = _indent(lines[key_line])
    end = key_line + 1
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            break
        if line.lstrip().startswith("#") and _indent(line) <= key_indent:
            break
        if _indent(line) <= key_indent and not line.lstrip().startswith("#"):
            break
        end += 1
    # do not swallow trailing comment lines that sit at the key's own indent
    while end > key_line + 1 and lines[end - 1].lstrip().startswith("#"):
        end -= 1
    return key_line, end


def set_scalar(lines: list[str], path: list[str], value: str) -> None:
    a, b = _find_key(lines, path)
    indent = " " * _indent(lines[a])
    lines[a:b] = [f"{indent}{path[-1]}: {value}"]


def drop_key(lines: list[str], path: list[str]) -> None:
    try:
        a, b = _find_key(lines, path)
    except KeyError:
        return
    # take any comment lines immediately above that explain this key
    while a > 0 and lines[a - 1].lstrip().startswith("#") and _indent(lines[a - 1]) == _indent(lines[a]):
        a -= 1
    del lines[a:b]


def yaml_str(text: str) -> str:
    """A double-quoted YAML scalar, safe for any one-line text."""
    return json.dumps(text, ensure_ascii=False)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args) -> int:
    rows = snapshots(load_manifests())
    if args.dataset:
        rows = [r for r in rows if r["dataset"] == args.dataset]
    if args.by_builder:
        # One leg per builder for the canary: a builder that writes a set
        # fetches once for all of them, so running it per dataset only
        # repeats the same fetch. One pass, first-seen order; the leg is
        # named for the builder's first dataset.
        by_builder: dict[str, dict] = {}
        for r in rows:
            leg = by_builder.setdefault(r["builder"], {**r, "datasets": []})
            leg["datasets"].append(r["dataset"])
        rows = list(by_builder.values())
    print(json.dumps(rows, indent=1))
    return 0


def cmd_due(args) -> int:
    today = dt.date.today()
    rows = []
    for row in snapshots(load_manifests()):
        due, why = (True, "forced with --all") if args.all else is_due(row, today)
        if args.dataset and row["dataset"] != args.dataset:
            continue
        print(f"{row['dataset']}: {'DUE' if due else 'skip'} — {why}", file=sys.stderr)
        if due:
            rows.append({**row, "why": why})
    print(json.dumps(rows, indent=1))
    return 0


def _load_summary(path: str, dataset: str) -> dict:
    """A builder writes one summary (a dict) or, when it produces a set of
    files, one per file (a list); either way, the entry for `dataset` — and
    refuse anything else. Not an assert: `python -O` would drop it, and this
    is the guard that stops one builder's summary from stamping, or
    describing, another dataset."""
    loaded = json.loads(pathlib.Path(path).read_text())
    entries = loaded if isinstance(loaded, list) else [loaded]
    matches = [s for s in entries if isinstance(s, dict) and s.get("dataset") == dataset]
    if not matches:
        found = sorted(str(s.get("dataset")) for s in entries if isinstance(s, dict))
        print(f"::error::{dataset}: no summary for it in {path} (found {found}) — refusing",
              file=sys.stderr)
        raise SystemExit(1)
    return matches[0]


def cmd_stamp(args) -> int:
    summary = _load_summary(args.summary, args.dataset)   # refuses a mismatch
    dataset = args.dataset
    data_path = LECTURES / dataset
    manifest_path = LECTURES / f"{dataset}.yml"
    today = dt.date.today().isoformat()
    digest = sha256(data_path)
    end = summary["date_range"]["end"]

    lines = manifest_path.read_text(encoding="utf-8").split("\n")
    set_scalar(lines, ["retrieved"], today)
    set_scalar(lines, ["integrity", "sha256"], digest)
    set_scalar(lines, ["integrity", "upstream", "status"], "verified")
    set_scalar(lines, ["integrity", "upstream", "date"], today)
    set_scalar(lines, ["integrity", "upstream", "against"], summary["builder"])
    overlap = summary.get("overlap") or {}
    note = (f"Refreshed {today} by the scheduled refresh: these bytes are the builder's "
            f"validated output from the live source that day, so they are verified by "
            f"construction. Overlap window {overlap.get('window', 'n/a')}: "
            f"{overlap.get('cells_revised', 0)} of {overlap.get('cells_total', 0)} cells "
            f"revised, max |change| {overlap.get('max_abs_change', 0)}.")
    set_scalar(lines, ["integrity", "upstream", "note"], yaml_str(note))
    for key in ("delta_kind", "delta", "delta_evidence", "register"):
        drop_key(lines, ["integrity", "upstream", key])
    a, b = _find_key(lines, ["schema", "date_range"])
    lines[a] = re.sub(r"end: [^,}]+", f"end: {end}", lines[a])
    text = "\n".join(lines)

    # Prove it reads back as intended before it lands.
    m = yaml.safe_load(text)
    up = m["integrity"]["upstream"]
    checks = {
        "retrieved": _iso(m["retrieved"]) == today,
        "sha256": m["integrity"]["sha256"] == digest,
        "status": up["status"] == "verified",
        "date": _iso(up["date"]) == today,
        "against": up["against"] == summary["builder"],
        "delta dropped": not any(k in up for k in ("delta_kind", "delta", "delta_evidence", "register")),
        # YAML reads a date-shaped scalar back as a date object; compare as text.
        "date_range.end": _iso(m["schema"]["date_range"]["end"]) == str(end),
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        print(f"::error::{dataset}.yml: stamp did not read back — {failed}", file=sys.stderr)
        return 1
    manifest_path.write_text(text, encoding="utf-8")
    print(f"stamped {manifest_path.name}: retrieved {today}, sha256 {digest[:12]}…, end {end}")
    return 0


def cmd_pr_body(args) -> int:
    summary = _load_summary(args.summary, args.dataset)
    dataset = args.dataset
    m = load_manifests()[dataset]
    ov = summary.get("overlap") or {}
    end = summary["date_range"]["end"]
    prev_end = ov.get("previous_end")
    title = (f"Refresh {dataset}: {prev_end} → {end}" if prev_end and prev_end != end
             else f"Refresh {dataset} ({end} vintage, values revised)")
    consumers = m.get("consumers") or []
    lines = [
        title,
        "",
        f"Scheduled refresh of `{dataset}` (`class: dynamic-snapshot`, `cadence: {m.get('cadence')}`) "
        f"by `{summary['builder']}` on {dt.date.today().isoformat()}. The builder fetched the live source, "
        f"validated the result against the published contract, and wrote it; the manifest is stamped to match "
        f"(`retrieved`, `integrity.sha256`, `integrity.upstream: verified`, `schema.date_range.end`) and "
        f"`CATALOG.md` is regenerated. Review this PR through the overlap summary below — it is the one place a "
        f"revision is a decision rather than a diff.",
        "",
        "| | |",
        "| --- | --- |",
        f"| Shape | {summary['rows']} rows × {summary['columns']} columns |",
        f"| Date range | {summary['date_range']['start']} to {end}" + (f" (was {prev_end})" if prev_end else "") + " |",
    ]
    if ov:
        lines += [
            f"| Overlap window | {ov['window']}: **{ov['cells_revised']} of {ov['cells_total']} cells revised**, max change {ov['max_abs_change']} |",
            f"| New columns | {', '.join(ov['new_columns']) if ov['new_columns'] else 'none'} |",
        ]
    lines += ["", "**Consumers** (from the manifest; AGENTS.md \"Refresh, break, or schema change\"):", ""]
    if consumers:
        for c in consumers:
            action = c.get("on_refresh", "unset")
            lines.append(f"- `{c.get('repo')}` — `{c.get('file')}` — `on_refresh: {action}`"
                         + (" → open an issue there with this summary" if action == "review"
                            else " → dispatch a rebuild" if action == "rebuild"
                            else " → decide, then record `on_refresh` in the manifest"))
    else:
        lines.append("- none recorded — nothing to rebuild or notify.")
    lines += ["", "_Opened automatically by `.github/workflows/refresh-snapshots.yml`. A later run of the same "
              "refresh updates this branch and PR rather than opening another._"]
    print("\n".join(lines))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--dataset"); p.add_argument("--by-builder", action="store_true")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("due"); p.add_argument("--all", action="store_true"); p.add_argument("--dataset")
    p.set_defaults(fn=cmd_due)
    p = sub.add_parser("stamp"); p.add_argument("dataset"); p.add_argument("--summary", required=True)
    p.set_defaults(fn=cmd_stamp)
    p = sub.add_parser("pr-body"); p.add_argument("dataset"); p.add_argument("--summary", required=True)
    p.set_defaults(fn=cmd_pr_body)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
