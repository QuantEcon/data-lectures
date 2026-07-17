#!/usr/bin/env python3
"""Generate the data-audit dashboard — scan the Python-family lecture repos,
classify every data reference, and render the gh-pages site.

Two stages, kept separate so the structured data is reusable (data-lectures#20):

    scan    grep each lecture repo's origin/main for data references, classify
            them, reconcile with the migrated-dataset manifests (lectures/*.yml)
            and the migration tracker (migration.yml), and write audit.json
    render  read audit.json and write the static dashboard into site/

    python scripts/build_audit.py scan   --repos-dir ../ -o audit.json
    python scripts/build_audit.py render --audit audit.json -o site/
    python scripts/build_audit.py all    --repos-dir ../ -o site/

Sources of truth, in order:
  - lectures/*.yml manifests  — migrated datasets (class, license, consumers)
  - migration.yml             — migration lifecycle + PR provenance
  - scripts/audit_annotations.yml — curated judgment for NOT-yet-migrated refs
    (descriptions, provenance class, flags, API series). The scan FAILS when a
    reference has neither a manifest nor an annotation, so new data reads in
    the lecture repos surface loudly instead of rotting silently.

Never use `gh search code` to find URLs — it tokenizes on `/` and `.` and
returns clean zeros. This script greps clones (workspace-lectures learned this
the hard way; see QuantEcon/data-lectures#20).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
LECTURES = REPO / "lectures"
ANNOTATIONS = REPO / "scripts" / "audit_annotations.yml"
MIGRATION = REPO / "migration.yml"

# The 8 synced Python-family repos (workspace-lectures manifest.yml scope).
# Translations and the topic-based series are out of scope by decision.
SCAN_REPOS = [
    "lecture-python-intro",
    "lecture-python-programming",
    "lecture-python.myst",
    "lecture-python-advanced.myst",
    "lecture-jax",
    "lecture-dp",
    "lecture-wasm",
    "continuous_time_mcs",
]

ORG = "quantecon"
THIS_REPO_NAMES = {"data-lectures", "data"}  # rename redirect
LEGACY_REPO_NAMES = {"lecture-python", "lecture-python.rst"}  # retired pre-MyST repo

DATA_EXT = {".csv", ".xlsx", ".xls", ".dta", ".npy", ".mat", ".json", ".txt",
            ".parquet", ".pkl", ".zip", ".ods"}

# Committed paths that carry a data extension but are not datasets.
COMMITTED_IGNORE = re.compile(
    r"(^|/)(\.github|_notebook_repo|_build)/"
    r"|(^|/)(requirements.*\.txt|robots\.txt|runtime\.txt|LICENSE.*|CNAME)$"
    r"|(^|/)(_config\.yml|_toc\.yml)$"
    r"|\.ipynb_checkpoints"
)

CODE_CELL = re.compile(r"^```\{code-cell\}[^\n]*\n(.*?)^```", re.M | re.S)
SKIP_TAGS = re.compile(r"^:tags:.*(skip-execution|remove-cell)", re.M)
QUOTED_DATA = re.compile(
    r"""['"]([^'"\s]+\.(?:csv|xlsx|xls|dta|npy|mat|json|txt|parquet|pkl|zip))
        (\?[^'"]*)?['"]""",
    re.X,
)
URL_RE = re.compile(r"https?://[^\s'\")\]}>]+")
PCT_FILE = re.compile(r"^%%(?:write)?file\s+(?:-\w+\s+)?(\S+)", re.M)
# in-lecture writes: a later read of the same file is embedded, not a dataset
INLINE_WRITE = re.compile(
    r"""open\(\s*['"]([^'"]+)['"]\s*,\s*(?:mode\s*=\s*)?['"][wa]b?['"]
        |\.to_csv\(\s*['"]([^'"]+)['"]
        |np\.save(?:txt)?\(\s*['"]([^'"]+)['"]""",
    re.X,
)
# python string plumbing the resolver understands
BACKSLASH_JOIN = re.compile(r"\\\s*\n\s*")
ADJACENT_LITS = re.compile(r"""(['"])([^'"\n]*)\1\s*(?:\+\s*)?\n?\s*(['"])([^'"\n]*)\3""")
STR_ASSIGN = re.compile(r"^[ \t]*(\w+)\s*=\s*(f?)(['\"])([^'\"\n]*)\3\s*$", re.M)
VAR_PLUS_LIT = re.compile(r"(\w+)\s*\+\s*(['\"])([^'\"\n]*)\2")
FSTRING_LIT = re.compile(r"f(['\"])([^'\"\n]*\{\w+\}[^'\"\n]*)\1")
INTERP = re.compile(r"\{(\w+)\}")


def resolve_strings(text: str):
    """Join continuations / adjacent literals, resolve simple string variables,
    and return (normalized_text, fully-resolved string expressions)."""
    text = BACKSLASH_JOIN.sub(" ", text)
    prev = None
    while prev != text:  # merge chains of adjacent/`+`-joined literals
        prev = text
        text = ADJACENT_LITS.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(4)}{m.group(1)}", text)

    values: dict[str, str] = {}
    for _ in range(3):  # a few passes resolve var → f-string → read chains
        for m in STR_ASSIGN.finditer(text):
            name, is_f, _, val = m.groups()
            if is_f:
                val = INTERP.sub(lambda i: values.get(i.group(1), i.group(0)), val)
            if "{" not in val:
                values[name] = val

    resolved = set(values.values())
    for m in FSTRING_LIT.finditer(text):
        val = INTERP.sub(lambda i: values.get(i.group(1), i.group(0)), m.group(2))
        if "{" not in val:
            resolved.add(val)
    for m in VAR_PLUS_LIT.finditer(text):
        var, _, lit = m.groups()
        if var in values:
            resolved.add(values[var] + lit)
    return text, sorted(resolved)

GH_URL_FORMS = [
    # (regex, canonical spelling label)
    (re.compile(r"https?://github\.com/([^/]+)/([^/]+)/raw/refs/heads/([^/]+)/(.+)"),
     "github.com/{org}/{repo}/raw/refs/heads/{ref}/…"),
    (re.compile(r"https?://github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+)"),
     "github.com/{org}/{repo}/raw/{ref}/…"),
    (re.compile(r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)\?raw=true"),
     "github.com/{org}/{repo}/blob/{ref}/…?raw=true"),
    (re.compile(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/refs/heads/([^/]+)/(.+)"),
     "raw.githubusercontent.com/{org}/{repo}/refs/heads/{ref}/…"),
    (re.compile(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)"),
     "raw.githubusercontent.com/{org}/{repo}/{ref}/…"),
    (re.compile(r"https?://media\.githubusercontent\.com/media/([^/]+)/([^/]+)/([^/]+)/(.+)"),
     "media.githubusercontent.com/media/{org}/{repo}/{ref}/…"),
]

API_MARKERS = [
    # (regex on a code line, provider, access label)
    (re.compile(r"\bwbgapi\b|\bwb\.(data|series|economy)\b"), "World Bank", "wbgapi"),
    (re.compile(r"pandas_datareader|\bDataReader\b|web\.DataReader"), "FRED", "pandas_datareader"),
    (re.compile(r"fredgraph\.csv"), "FRED", "fredgraph.csv URL"),
    (re.compile(r"\byfinance\b|\byf\.(download|Ticker)\b"), "Yahoo Finance", "yfinance"),
]


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


def git_show(repo_dir: Path, path: str) -> str:
    return run(["git", "show", f"origin/main:{path}"], repo_dir)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def classify_url(url: str, consuming_repo: str):
    """Classify a URL → (pattern, detail dict) or None if not a data URL."""
    scan_repos_l = {r.lower() for r in SCAN_REPOS}
    for rx, form in GH_URL_FORMS:
        m = rx.match(url)
        if not m:
            continue
        org, repo, ref, path = m.groups()
        if Path(path.split("?")[0]).suffix.lower() not in DATA_EXT:
            return None  # partial URL from an unresolved continuation, or non-data
        repo_l = repo.lower().removesuffix(".git")
        if org.lower() != ORG:
            pattern = "external"
        elif repo_l in THIS_REPO_NAMES:
            pattern = "data-lectures"
        elif repo_l == consuming_repo.lower():
            pattern = "own-repo"
        elif repo_l in LEGACY_REPO_NAMES:
            pattern = "legacy"
        elif repo_l in scan_repos_l:
            pattern = "sibling"
        else:
            pattern = "external"
        return pattern, {
            "org": org, "gh_repo": repo, "ref": ref, "path": path,
            "url_form": form,
            "branch_pinned": ref not in ("main", "master", "gh-pages"),
            "lfs_media": "media.githubusercontent.com" in url,
        }
    if "fredgraph.csv" in url:
        return "api", {"provider": "FRED", "access": "fredgraph.csv URL"}
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext in DATA_EXT:
        return "external-web", {"url_form": "non-GitHub host"}
    return None


def scan_repo(name: str, repos_dir: Path):
    repo_dir = repos_dir / name
    if not (repo_dir / ".git").exists():
        sys.exit(f"error: {repo_dir} is not a git clone (run `make sync` "
                 f"in the workspace, or pass --repos-dir)")
    sha = run(["git", "rev-parse", "--short", "origin/main"], repo_dir).strip()
    tree = run(["git", "ls-tree", "-r", "--name-only", "origin/main"],
               repo_dir).splitlines()

    lecture_files = [p for p in tree
                     if p.startswith("lectures/") and p.endswith(".md")]
    committed = [p for p in tree
                 if Path(p).suffix.lower() in DATA_EXT
                 and not COMMITTED_IGNORE.search(p)]

    refs = []       # static/embedded reads
    api_uses = []   # (lecture, provider, access)
    for lf in lecture_files:
        text = git_show(repo_dir, lf)
        cells = "\n".join(c for c in CODE_CELL.findall(text)
                          if not SKIP_TAGS.search(c))
        if not cells:
            continue
        lecture = Path(lf).stem
        cells, resolved = resolve_strings(cells)

        embedded_targets = {t for t in PCT_FILE.findall(cells)
                            if Path(t).suffix.lower() in DATA_EXT}
        embedded_targets |= {t for g in INLINE_WRITE.findall(cells)
                             for t in g if t
                             and Path(t).suffix.lower() in DATA_EXT}
        for tgt in sorted(embedded_targets):
            refs.append({"repo": name, "lecture": lecture, "lecture_path": lf,
                         "file": Path(tgt).name, "target": tgt,
                         "pattern": "embedded"})

        # candidate targets: raw URLs, resolved string expressions, quoted paths
        candidates = []
        for url in URL_RE.findall(cells):
            candidates.append(url.rstrip("'\".,;:"))
        candidates += [r for r in resolved
                       if "://" in r or Path(r).suffix.lower() in DATA_EXT]
        for m in QUOTED_DATA.finditer(cells):
            if "{" in m.group(1):
                continue  # unresolved f-string piece
            if re.search(r"[\w\)\]]\s*\+\s*['\"]$", cells[:m.start() + 1]):
                continue  # suffix of a var + 'literal' concat — resolved above
            candidates.append(m.group(1))

        seen = set()
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)
            if cand.startswith(("http://", "https://")):
                got = classify_url(cand, name)
                if not got:
                    continue
                pattern, detail = got
                if pattern == "api":
                    api_uses.append((lecture, detail["provider"], detail["access"]))
                    continue
                refs.append({"repo": name, "lecture": lecture, "lecture_path": lf,
                             "file": Path(detail.get("path", cand).split("?")[0]).name,
                             "target": cand, "pattern": pattern, **detail})
            else:
                if Path(cand).suffix.lower() not in DATA_EXT:
                    continue
                base = Path(cand).name
                if base in {Path(t).name for t in embedded_targets}:
                    continue  # read-back of an in-lecture write — Registry B
                refs.append({"repo": name, "lecture": lecture, "lecture_path": lf,
                             "file": base, "target": cand, "pattern": "local-path"})

        for rx, provider, access in API_MARKERS:
            if rx.search(cells):
                api_uses.append((lecture, provider, access))

    # dedupe: one row per (lecture, pattern, target)
    uniq, out = set(), []
    for r in refs:
        key = (r["lecture"], r["pattern"], r["target"])
        if key not in uniq:
            uniq.add(key)
            out.append(r)
    api = sorted({(l, p, a) for l, p, a in api_uses})
    return {"sha": sha, "refs": out, "committed": committed,
            "api": [{"lecture": l, "provider": p, "access": a} for l, p, a in api]}


def committed_referenced(repo: str, committed: list[str], all_refs: list[dict]):
    """Which committed data files does some lecture actually read?"""
    referenced = set()
    for path in committed:
        base = Path(path).name
        for r in all_refs:
            if r["pattern"] == "embedded":
                continue  # a %%file cell shadows, it does not reference
            if r["pattern"] == "local-path" and r["repo"] == repo:
                tgt = r["target"].lstrip("./")
                cands = {f"lectures/{tgt}", tgt,
                         str(Path(r["lecture_path"]).parent / tgt)}
                if path in cands:
                    referenced.add(path)
            elif r.get("gh_repo", "").lower() == repo.lower():
                if r.get("path", "").strip("/") == path:
                    referenced.add(path)
            elif r["pattern"] == "local-path" and r["repo"] == repo and \
                    Path(r["target"]).name == base:
                referenced.add(path)
    return referenced


def load_yaml(path: Path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_manifests():
    manifests = {}
    for p in sorted(LECTURES.glob("*.yml")):
        m = load_yaml(p)
        if isinstance(m, dict) and "filename" in m:
            data_file = LECTURES / m["filename"]
            m["_size"] = data_file.stat().st_size if data_file.exists() else None
            manifests[m["filename"]] = m
    return manifests


def scan(repos_dir: Path):
    ann = load_yaml(ANNOTATIONS)
    ignore = set(ann.get("ignore_targets", []))
    ignore_committed = set(ann.get("ignore_committed", []))
    datasets_ann = ann.get("datasets", {})
    api_ann = ann.get("api", {})
    orphan_ann = ann.get("committed_unreferenced", {})

    manifests = load_manifests()
    migration = load_yaml(MIGRATION)

    repos, all_refs, all_api = {}, [], []
    for name in SCAN_REPOS:
        res = scan_repo(name, repos_dir)
        res["refs"] = [r for r in res["refs"] if r["target"] not in ignore]
        repos[name] = {"sha": res["sha"], "committed": res["committed"]}
        all_refs += res["refs"]
        for a in res["api"]:
            all_api.append({"repo": name, **a})

    # committed-but-unreferenced sweep
    orphans = []
    n_committed = 0
    for name in SCAN_REPOS:
        committed = [p for p in repos[name]["committed"]
                     if f"{name}:{p}" not in ignore_committed]
        repos[name]["committed"] = committed
        n_committed += len(committed)
        used = committed_referenced(name, committed, all_refs)
        for path in committed:
            if path not in used:
                note = orphan_ann.get(f"{name}:{path}", {})
                orphans.append({"repo": name, "path": path,
                                "kind": note.get("kind", "orphan"),
                                "note": note.get("note", "")})

    # aggregate static refs into datasets keyed by basename
    static = [r for r in all_refs if r["pattern"] not in ("embedded",)]
    embedded = [r for r in all_refs if r["pattern"] == "embedded"]
    by_file = defaultdict(list)
    for r in static:
        by_file[r["file"]].append(r)

    datasets, missing_ann = [], []
    for fname, rows in sorted(by_file.items()):
        manifest = manifests.get(fname)
        a = datasets_ann.get(fname, {})
        if not manifest and not a:
            missing_ann.append(fname)
        patterns = sorted({r["pattern"] for r in rows})
        migrated = "data-lectures" in patterns
        fully_migrated = migrated and patterns == ["data-lectures"]
        datasets.append({
            "file": fname,
            "refs": rows,
            "patterns": patterns,
            "consumers": sorted({(r["repo"], r["lecture"]) for r in rows}),
            "migrated": migrated,
            "fully_migrated": fully_migrated,
            "manifest": bool(manifest),
            "description": (manifest or {}).get("title") or a.get("description", ""),
            "provenance": ((manifest or {}).get("class") or a.get("provenance", "")),
            "flags": a.get("flags", []),
            "note": a.get("note", ""),
        })

    # API registry: mechanical detection enriched by annotations
    api_rows, api_missing = [], []
    for u in all_api:
        key = f"{u['repo']}:{u['lecture']}:{u['access']}"
        a = api_ann.get(key)
        if a is None:
            api_missing.append(key)
            a = {}
        api_rows.append({**u, "series": a.get("series", ""),
                         "pedagogy": a.get("pedagogy", ""),
                         "note": a.get("note", "")})

    # migration.yml vs reality: the check that keeps the tracker honest
    mig_problems = []
    by_name = {d["file"]: d for d in datasets}
    for fname, rec in (migration.get("datasets") or {}).items():
        d = by_name.get(fname)
        status = rec.get("status")
        if status in ("repointed", "final"):
            if d is None:
                mig_problems.append(
                    f"{fname}: marked {status} but no lecture reads it at all")
            elif not d["fully_migrated"]:
                stale = sorted({r["pattern"] for r in d["refs"]} - {"data-lectures"})
                mig_problems.append(
                    f"{fname}: marked {status} but consumers still read via {stale}")
        elif status in ("pending", "landed") and d and d["migrated"]:
            mig_problems.append(
                f"{fname}: marked {status} but some consumer already reads data-lectures")
        if status in ("landed", "repointed", "final") and fname not in manifests:
            mig_problems.append(f"{fname}: marked {status} but has no manifest")
    for fname, m in manifests.items():
        if fname not in (migration.get("datasets") or {}):
            mig_problems.append(f"{fname}: has a manifest but no migration.yml record")
    for wave in migration.get("pending") or []:
        for fname in wave.get("datasets") or []:
            d = by_name.get(fname)
            if d and d["migrated"]:
                mig_problems.append(
                    f"{fname}: in pending wave {wave.get('pilot')} but already "
                    f"read from data-lectures")

    audit = {
        "generated": date.today().isoformat(),
        "repos": {n: {"sha": repos[n]["sha"],
                      "n_committed": len(repos[n]["committed"])}
                  for n in SCAN_REPOS},
        "datasets": datasets,
        "embedded": embedded,
        "api": api_rows,
        "orphans": orphans,
        "manifests": {k: {
            "title": m.get("title"), "class": m.get("class"),
            "license": (m.get("license") or {}).get("name"),
            "redistribution": (m.get("license") or {}).get("redistribution"),
            "integrity": ((m.get("integrity") or {}).get("upstream") or {}).get("status"),
            "builder_status": m.get("builder_status"),
            "size": m.get("_size"),
            "consumers": m.get("consumers") or [],
        } for k, m in manifests.items()},
        "migration": migration,
        "problems": {
            "missing_annotations": sorted(missing_ann),
            "missing_api_annotations": sorted(api_missing),
            "migration_inconsistencies": mig_problems,
        },
        "stats": {
            "static_files": len(datasets),
            "committed_files": n_committed,
            "orphans": len(orphans),
            "legacy_refs": sum(1 for r in static if r["pattern"] == "legacy"),
            "migrated": sum(1 for d in datasets if d["fully_migrated"]),
            "api_lectures": len({(u["repo"], u["lecture"]) for u in all_api}),
            "url_forms": len({r.get("url_form") for r in static if r.get("url_form")}),
        },
    }
    return audit


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["scan", "render", "all"])
    ap.add_argument("--repos-dir", type=Path,
                    default=REPO.parent,
                    help="directory containing the lecture repo clones "
                         "(default: this repo's parent, i.e. the workspace repos/)")
    ap.add_argument("--audit", type=Path, default=REPO / "audit.json")
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--strict", action="store_true",
                    help="fail when a data reference has no annotation/manifest")
    args = ap.parse_args()

    if args.stage in ("scan", "all"):
        audit = scan(args.repos_dir)
        out = args.out if (args.out and args.stage == "scan") else args.audit
        out.write_text(json.dumps(audit, indent=1, default=str), encoding="utf-8")
        probs = audit["problems"]
        for key, items in probs.items():
            for it in items:
                print(f"warning: {key}: {it}", file=sys.stderr)
        print(f"wrote {out} — {audit['stats']['static_files']} static files, "
              f"{audit['stats']['orphans']} orphans, "
              f"{audit['stats']['api_lectures']} live-API lectures")
        if args.strict and any(probs.values()):
            return 1

    if args.stage in ("render", "all"):
        from render_audit import render  # noqa: deferred import, same dir
        audit = json.loads(args.audit.read_text(encoding="utf-8"))
        site = args.out or (REPO / "site")
        render(audit, site)
        print(f"wrote {site}/")

    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main())
