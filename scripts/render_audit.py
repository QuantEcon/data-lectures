#!/usr/bin/env python3
"""Render the data-audit dashboard (site/) from audit.json.

Invoked by build_audit.py's `render` stage; not usually run directly. The
design system evolves the 2026-07-15 audit artifact: same theme-aware palette,
pattern/provenance pills and table language, extended with a top nav, a landing
page with the migration meter, and the per-dataset lifecycle stepper.

Chart colors are validated (dataviz six-checks) — meter series:
light #2c7a44/#1f6fb2, dark #42a065/#3f8ec7, neutral track for the remainder.
Pills are labeled (identity never rides on color alone).
"""
from __future__ import annotations

import html
from pathlib import Path

GH = "https://github.com"
DL = f"{GH}/QuantEcon/data-lectures"
RAW = f"{DL}/raw/main/lectures"
PREV_SNAPSHOT = "2026-07-15"

PATTERN_META = {
    # key: (pill css class, label, one-line description)
    "data-lectures": ("p-dl", "data-lectures", "reads this repo's published tree — the target state"),
    "own-repo": ("p-own", "own-repo URL", "fetches a file committed in its own repo via a GitHub raw URL"),
    "local-path": ("p-local", "local path", "pd.read_csv('…') relative path — no URL; breaks in Colab/download"),
    "sibling": ("p-sib", "sibling repo URL", "fetches another lecture repo's committed copy by URL"),
    "external": ("p-ext", "external data repo", "QuantEcon/high_dim_data via raw and media (LFS) hosts"),
    "external-web": ("p-ext", "external web host", "fetches a data file from a non-GitHub host by URL"),
    "legacy": ("p-legacy", "legacy-repo URL", "fetches from the retired pre-MyST lecture-python repo"),
    "embedded": ("p-embed", "%%file embedded", "written by the lecture itself, then read back"),
    "api": ("p-api", "live API", "fetched at build time from a third-party service"),
}

PROVENANCE_META = {
    "verbatim": ("p-own", "verbatim", "third-party file as distributed; the citation is the provenance"),
    "constructed-committed": ("p-local", "constructed · builder committed", "built by a script/notebook that is committed"),
    "constructed-lost": ("p-legacy", "constructed · pipeline lost", "construction documented but never committed"),
    "author-assembled": ("p-ext", "author-assembled", "hand-built by authors; provenance is lecture prose only"),
    "toy": ("p-embed", "toy", "invented in-lecture teaching data"),
}

ORPHAN_KIND = {
    "orphan": ("p-legacy", "orphan"),
    "shadowed": ("p-embed", "shadowed"),
    "superseded": ("p-legacy", "superseded"),
    "mirror-orphan": ("p-embed", "mirror-orphan"),
    "exercise-download": ("p-own", "exercise download"),
}

PEDAGOGY_META = {
    "lesson": ("p-local", "API is the lesson"),
    "mixed": ("p-own", "mixed"),
    "incidental": ("p-legacy", "incidental"),
}

STATUS_STEPS = ["pending", "landed", "repointed", "final"]

CSS = """
:root {
  --bg: #f6f8f9; --surface: #ffffff; --ink: #1f262c; --muted: #5a6673;
  --line: #dde3e8; --accent: #1f6fb2; --accent-ink: #ffffff;
  --warn: #9a6700; --warn-bg: #fdf3d7; --crit: #b3352b; --crit-bg: #fbe9e7;
  --ok: #2c7a44; --ok-bg: #e2f2e6;
  --own-bg: #e3eef8; --own-ink: #1a5c96;
  --legacy-bg: #fdf3d7; --legacy-ink: #9a6700;
  --ext-bg: #ede8f7; --ext-ink: #5b3f9e;
  --local-bg: #e2f2e6; --local-ink: #23703a;
  --embed-bg: #e9edf0; --embed-ink: #4d5a66;
  --api-bg: #dff2f1; --api-ink: #0e6b66;
  --dl-bg: #f7e6ef; --dl-ink: #a1336b;
  --sib-bg: #f3ece1; --sib-ink: #7a5327;
  --code-bg: #eef1f4;
  --meter-a: #2c7a44; --meter-b: #1f6fb2; --meter-track: #e4e9ed;
}
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1a2128; --ink: #dee5eb; --muted: #8a97a3;
  --line: #2a333c; --accent: #5fa8dc; --accent-ink: #0e1418;
  --warn: #e3b341; --warn-bg: #3a2f10; --crit: #f2857a; --crit-bg: #43201c;
  --ok: #7fce97; --ok-bg: #16321e;
  --own-bg: #17324a; --own-ink: #8ec4ea;
  --legacy-bg: #3a2f10; --legacy-ink: #e3b341;
  --ext-bg: #2c2344; --ext-ink: #b8a3e8;
  --local-bg: #16321e; --local-ink: #7fce97;
  --embed-bg: #242c33; --embed-ink: #9aa8b4;
  --api-bg: #0f3230; --api-ink: #6fcdc6;
  --dl-bg: #3c1e30; --dl-ink: #e08fc0;
  --sib-bg: #342a1a; --sib-ink: #d3a95e;
  --code-bg: #232b33;
  --meter-a: #42a065; --meter-b: #3f8ec7; --meter-track: #2a333c;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #12171c; --surface: #1a2128; --ink: #dee5eb; --muted: #8a97a3;
    --line: #2a333c; --accent: #5fa8dc; --accent-ink: #0e1418;
    --warn: #e3b341; --warn-bg: #3a2f10; --crit: #f2857a; --crit-bg: #43201c;
    --ok: #7fce97; --ok-bg: #16321e;
    --own-bg: #17324a; --own-ink: #8ec4ea;
    --legacy-bg: #3a2f10; --legacy-ink: #e3b341;
    --ext-bg: #2c2344; --ext-ink: #b8a3e8;
    --local-bg: #16321e; --local-ink: #7fce97;
    --embed-bg: #242c33; --embed-ink: #9aa8b4;
    --api-bg: #0f3230; --api-ink: #6fcdc6;
    --dl-bg: #3c1e30; --dl-ink: #e08fc0;
    --sib-bg: #342a1a; --sib-ink: #d3a95e;
    --code-bg: #232b33;
    --meter-a: #42a065; --meter-b: #3f8ec7; --meter-track: #2a333c;
  }
}
* { box-sizing: border-box; }
body {
  background: var(--bg); color: var(--ink);
  font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
  font-size: 15px; line-height: 1.55; margin: 0;
}
main { max-width: 1100px; margin: 0 auto; padding: 28px 28px 80px; }
nav.top {
  background: var(--surface); border-bottom: 1px solid var(--line);
  position: sticky; top: 0; z-index: 10;
}
nav.top .inner {
  max-width: 1100px; margin: 0 auto; padding: 10px 28px;
  display: flex; align-items: center; gap: 22px; flex-wrap: wrap;
}
nav.top .brand { font-weight: 650; font-size: 15px; color: var(--ink); text-decoration: none; }
nav.top .brand span { color: var(--accent); }
nav.top a.item {
  color: var(--muted); text-decoration: none; font-size: 14px; padding: 3px 2px;
  border-bottom: 2px solid transparent;
}
nav.top a.item:hover { color: var(--ink); }
nav.top a.item.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
nav.top button.theme {
  margin-left: auto; background: none; border: 1px solid var(--line); border-radius: 6px;
  color: var(--muted); font-size: 13px; padding: 3px 10px; cursor: pointer;
}
header.doc { border-bottom: 2px solid var(--accent); padding-bottom: 20px; margin-bottom: 28px; }
.eyebrow { text-transform: uppercase; letter-spacing: 0.09em; font-size: 12px; color: var(--accent); font-weight: 600; margin: 18px 0 6px; }
h1 { font-size: 30px; line-height: 1.2; margin: 0 0 10px; font-weight: 650; text-wrap: balance; }
.meta { color: var(--muted); font-size: 13.5px; margin: 0; }
.meta code { font-size: 12px; }
h2 { font-size: 21px; margin: 44px 0 6px; font-weight: 650; text-wrap: balance; }
h2 .sec { color: var(--accent); font-variant-numeric: tabular-nums; margin-right: 8px; }
h3 { font-size: 16px; margin: 26px 0 4px; font-weight: 650; }
p { max-width: 76ch; }
p.lede { color: var(--muted); margin-top: 0; }
code, .mono {
  font-family: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
  font-size: 12.8px;
}
code { background: var(--code-bg); padding: 1px 5px; border-radius: 3px; }
a { color: var(--accent); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 22px 0 6px; }
.stat { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; }
.stat b { display: block; font-size: 26px; font-weight: 650; font-variant-numeric: tabular-nums; line-height: 1.15; }
.stat span { font-size: 12.5px; color: var(--muted); line-height: 1.3; display: block; margin-top: 3px; }
.stat.warn b { color: var(--warn); }
.stat.crit b { color: var(--crit); }
.stat.ok b { color: var(--ok); }
.tablewrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; margin: 14px 0 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th {
  text-align: left; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); font-weight: 600; padding: 9px 12px; border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
td { padding: 8px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:last-child td { border-bottom: none; }
td.num { font-variant-numeric: tabular-nums; text-align: right; }
tr.group td {
  background: var(--code-bg); font-weight: 650; font-size: 12.5px;
  text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); padding: 6px 12px;
}
.pill {
  display: inline-block; border-radius: 99px; padding: 1.5px 9px; font-size: 11.5px;
  font-weight: 600; white-space: nowrap; letter-spacing: 0.01em;
}
.p-own { background: var(--own-bg); color: var(--own-ink); }
.p-legacy { background: var(--legacy-bg); color: var(--legacy-ink); }
.p-ext { background: var(--ext-bg); color: var(--ext-ink); }
.p-local { background: var(--local-bg); color: var(--local-ink); }
.p-embed { background: var(--embed-bg); color: var(--embed-ink); }
.p-api { background: var(--api-bg); color: var(--api-ink); }
.p-dl { background: var(--dl-bg); color: var(--dl-ink); }
.p-sib { background: var(--sib-bg); color: var(--sib-ink); }
.flag { color: var(--warn); font-weight: 600; font-size: 12.5px; }
.flag.crit { color: var(--crit); }
.flag.ok { color: var(--ok); }
.note { color: var(--muted); font-size: 13px; }
ul { padding-left: 22px; }
li { margin: 3px 0; }
.finding { background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 4px; padding: 12px 16px; margin: 10px 0; }
.finding.warn { border-left-color: var(--warn); }
.finding.crit { border-left-color: var(--crit); }
.finding.ok { border-left-color: var(--ok); }
.finding b { font-weight: 650; }
.finding p { margin: 4px 0 0; font-size: 13.5px; color: var(--muted); max-width: none; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 10px 0 4px; font-size: 12.5px; color: var(--muted); align-items: center; }
.legend .key { display: inline-flex; align-items: center; gap: 6px; }
.legend .swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
/* migration meter — 2 series + neutral track, 2px gaps, direct labels */
.meter { display: flex; height: 26px; border-radius: 6px; overflow: hidden; background: var(--meter-track); margin: 14px 0 6px; }
.meter .seg { height: 100%; }
.meter .seg + .seg { margin-left: 2px; }
.meter .seg.a { background: var(--meter-a); }
.meter .seg.b { background: var(--meter-b); }
.meter.mini { height: 8px; max-width: 340px; margin: 6px 0 2px; border-radius: 4px; }
tr.row-migrated td { background: var(--ok-bg); }
.freshness {
  display: inline-block; border-radius: 6px; padding: 4px 12px; margin-top: 12px;
  font-size: 13px; font-weight: 600;
  background: var(--ok-bg); color: var(--ok); border: 1px solid var(--line);
}
.freshness.warn { background: var(--warn-bg); color: var(--warn); }
.freshness.crit { background: var(--crit-bg); color: var(--crit); }
/* bar list — one measure, single hue, labeled rows */
.barlist { display: grid; grid-template-columns: max-content 1fr max-content; gap: 6px 12px; align-items: center; margin: 14px 0; }
.barlist .lbl { font-size: 13px; }
.barlist .bar { height: 14px; border-radius: 0 4px 4px 0; background: var(--accent); min-width: 2px; }
.barlist .val { font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted); }
/* landing nav cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin: 20px 0; }
.card {
  display: block; background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
  padding: 16px 18px; text-decoration: none; color: var(--ink);
}
.card:hover { border-color: var(--accent); }
.card b { display: block; font-size: 16px; font-weight: 650; margin-bottom: 4px; color: var(--accent); }
.card span { font-size: 13px; color: var(--muted); }
/* lifecycle stepper */
.pipeline { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; margin: 12px 0; }
.pipeline .head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.pipeline .head .name { font-weight: 650; font-size: 15px; }
.steps { display: flex; align-items: flex-start; }
.step { flex: 1; text-align: center; position: relative; min-width: 70px; }
.step .dot {
  width: 14px; height: 14px; border-radius: 50%; margin: 0 auto 6px;
  background: var(--surface); border: 2px solid var(--line); position: relative; z-index: 1;
}
.step.done .dot { background: var(--ok); border-color: var(--ok); }
.step.next .dot { border-color: var(--muted); }
.step::before {
  content: ""; position: absolute; top: 6px; left: -50%; width: 100%; height: 2px;
  background: var(--line);
}
.step:first-child::before { display: none; }
.step.done::before { background: var(--ok); }
.step .slbl { font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }
.step.done .slbl { color: var(--ok); }
.step .sdetail { font-size: 12px; color: var(--muted); margin-top: 2px; line-height: 1.4; }
footer {
  border-top: 1px solid var(--line); margin-top: 60px; padding-top: 16px;
  color: var(--muted); font-size: 12.5px;
}
@media (max-width: 640px) { h1 { font-size: 24px; } main { padding: 20px 16px 60px; } }
"""

THEME_JS = """
(function () {
  var saved = null;
  try { saved = localStorage.getItem('audit-theme'); } catch (e) {}
  if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved;
  window.toggleTheme = function () {
    var cur = document.documentElement.dataset.theme;
    if (!cur) cur = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    var next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('audit-theme', next); } catch (e) {}
  };
})();
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def pill(kind_map: dict, key: str) -> str:
    css, label = kind_map.get(key, ("p-embed", key))[:2]
    return f'<span class="pill {css}">{esc(label)}</span>'


def pattern_pill(p: str) -> str:
    return pill(PATTERN_META, p)


def repo_link(repo: str) -> str:
    return f'<a href="{GH}/QuantEcon/{esc(repo)}">{esc(repo)}</a>'


def lecture_link(repo: str, path: str, label: str) -> str:
    return f'<a href="{GH}/QuantEcon/{esc(repo)}/blob/main/{esc(path)}">{esc(label)}</a>'


def pr_link(ref: str) -> str:
    """QuantEcon/repo#N → link."""
    if not ref or "#" not in str(ref):
        return esc(ref)
    repo, num = str(ref).rsplit("#", 1)
    short = repo.split("/")[-1]
    return f'<a href="{GH}/{esc(repo)}/pull/{esc(num)}">{esc(short)}#{esc(num)}</a>'


def issue_link(ref: str) -> str:
    if not ref or "#" not in str(ref):
        return esc(ref)
    repo, num = str(ref).rsplit("#", 1)
    short = repo.split("/")[-1]
    return f'<a href="{GH}/{esc(repo)}/issues/{esc(num)}">{esc(short)}#{esc(num)}</a>'


def page(title: str, active: str, body: str, audit: dict) -> str:
    nav_items = [("index.html", "overview", "Overview"),
                 ("migration.html", "migration", "Migration tracker"),
                 ("audit.html", "audit", "Full audit")]
    nav = "".join(
        f'<a class="item{" active" if key == active else ""}" href="{href}">{label}</a>'
        for href, key, label in nav_items)
    shas = " · ".join(f"{esc(n)} <code>{esc(v['sha'])}</code>"
                      for n, v in audit["repos"].items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
<script>{THEME_JS}</script>
</head>
<body>
<nav class="top"><div class="inner">
<a class="brand" href="index.html">QuantEcon <span>data audit</span></a>
{nav}
<a class="item" href="{DL}">Repo ↗</a>
<button class="theme" onclick="toggleTheme()">◐ theme</button>
</div></nav>
<main>
{body}
<footer>
Generated {esc(audit["generated"])} by <a href="{DL}/blob/main/scripts/build_audit.py">scripts/build_audit.py</a>
from each repo's <code>origin/main</code>: {shas}.
Relates to {issue_link("QuantEcon/data-lectures#20")} · {issue_link("QuantEcon/meta#336")}.
</footer>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Page: overview (index.html)
# ---------------------------------------------------------------------------

def migration_meter(audit: dict) -> str:
    mig = audit["migration"] or {}
    recs = mig.get("datasets") or {}
    n_total = audit["stats"]["static_files"]
    n_repointed = sum(1 for r in recs.values() if r.get("status") in ("repointed", "final"))
    n_landed = sum(1 for r in recs.values() if r.get("status") == "landed")
    queued = sorted({f for w in (mig.get("pending") or []) for f in w.get("datasets") or []})
    pct = lambda n: max(0.8, 100 * n / n_total) if n else 0
    segs = ""
    if n_repointed:
        segs += f'<div class="seg a" style="width:{pct(n_repointed):.1f}%" title="repointed: {n_repointed}"></div>'
    if n_landed:
        segs += f'<div class="seg b" style="width:{pct(n_landed):.1f}%" title="landed: {n_landed}"></div>'
    return f"""
<h3>Migration progress</h3>
<div class="meter" role="img" aria-label="{n_repointed} of {n_total} static datasets repointed to data-lectures">{segs}</div>
<div class="legend">
<span class="key"><span class="swatch" style="background:var(--meter-a)"></span>migrated — every consuming lecture reads the central copy ({n_repointed})</span>
<span class="key"><span class="swatch" style="background:var(--meter-b)"></span>copied here, lectures not yet switched ({n_landed})</span>
<span class="key"><span class="swatch" style="background:var(--meter-track); border:1px solid var(--line)"></span>not migrated ({n_total - n_repointed - n_landed}, of which {len(queued)} queued for the next waves)</span>
</div>
<p class="note">Denominator: the {n_total} distinct static files lectures read today. The full
per-series manifest and the milestone plan are on the
<a href="migration.html">migration tracker</a>.</p>
"""


def pattern_barlist(audit: dict) -> str:
    counts: dict[str, int] = {}
    for d in audit["datasets"]:
        for r in d["refs"]:
            counts[r["pattern"]] = counts.get(r["pattern"], 0) + 1
    counts["embedded"] = len(audit["embedded"])
    counts["api"] = len({(u["repo"], u["lecture"]) for u in audit["api"]})
    order = [k for k in PATTERN_META if k in counts]
    mx = max(counts.values())
    rows = ""
    for k in order:
        unit = "lectures" if k == "api" else "refs"
        rows += (f'<div class="lbl">{pattern_pill(k)}</div>'
                 f'<div class="bar" style="width:{100 * counts[k] / mx:.1f}%"></div>'
                 f'<div class="val">{counts[k]} {unit}</div>')
    return f"""
<h3>Where lecture data comes from today</h3>
<div class="barlist">{rows}</div>
<p class="note">Counts are lecture→file references (a file read by two lectures counts twice);
the live-API row counts lectures. Full taxonomy on the <a href="audit.html">audit page</a>.</p>
"""


def what_changed() -> str:
    # The narrative diff vs the hand-built 2026-07-15 artifact. Static prose:
    # it describes a fixed historical comparison, not live state.
    return f"""
<h2>What moved since the {PREV_SNAPSHOT} snapshot</h2>
<p class="lede">The audit was first taken by hand on {PREV_SNAPSHOT}. Regenerating from live
repo state two days later, the picture has already changed — which is why this dashboard is generated.</p>
<div class="finding ok"><b>4 datasets migrated.</b>
<p>The first two migration waves moved <code>lingcod_msy_recovery.csv</code> (was a
Colab-breaking local path) and the <code>pandas_panel</code> trio <code>realwage.csv</code> /
<code>countries.csv</code> / <code>employ.csv</code> (5 of their 6 reads pointed at the retired
legacy repo). Every consuming lecture now reads the central copy. Details on the
<a href="migration.html">migration tracker</a>.</p></div>
<div class="finding ok"><b>Legacy-repo URLs: 8 → 0.</b>
<p>The pre-MyST <code>QuantEcon/lecture-python</code> repo was renamed to
<code>lecture-python.rst</code> and archived; the P2 repoints plus the <code>ols</code>
maketable repoint (lecture-python.myst#966) and the retirement sweeps
(lecture-python-programming#576, lecture-python.myst#968) removed every live reference.</p></div>
<div class="finding ok"><b>Branch-pinned refs: 1 → 0.</b>
<p>The critical flag on <code>SCF_plus_mini_no_weights.csv</code> — pinned to a feature branch of
high_dim_data — was fixed by lecture-python-intro#793; it now reads <code>main</code>.</p></div>
<div class="finding"><b>lecture-wasm joined the audit — and changed one fact.</b>
<p>The WASM mirror carries its own copies of intro's data files (all unread — its lectures fetch
intro's copies by URL), and its <code>short_path</code> fetches intro's committed
<code>graph.txt</code> over the network. That file was "shadowed dead weight" in the prior audit;
it is now load-bearing.</p></div>
<div class="finding warn"><b>2 new datasets appeared (lecture-python-intro#790).</b>
<p><code>us_adult_heights.csv</code> and <code>japan_population_by_age.xlsx</code> entered
<code>prob_dist</code> as local-path reads — the pattern P1 just migrated away from. New data
keeps arriving under the old conventions until the styleguide
({issue_link("QuantEcon/QuantEcon.manual#108")}) lands.</p></div>
"""


def render_index(audit: dict) -> str:
    s = audit["stats"]
    tiles = f"""
<div class="stats">
<div class="stat"><b>{s["static_files"]}</b><span>distinct static data files referenced by lectures</span></div>
<div class="stat ok"><b>{s["migrated"]}</b><span>migrated — every consumer reads data-lectures</span></div>
<div class="stat"><b>{s["api_lectures"]}</b><span>lectures fetching live third-party API data</span></div>
<div class="stat warn"><b>{s["orphans"]}</b><span>committed data files no lecture references</span></div>
<div class="stat ok"><b>{s["legacy_refs"]}</b><span>live URLs into the retired legacy repo (was 8)</span></div>
<div class="stat"><b>{s["url_forms"]}</b><span>GitHub URL spellings in use (was 6)</span></div>
</div>
"""
    cards = f"""
<div class="cards">
<a class="card" href="migration.html"><b>Migration tracker →</b>
<span>Per-dataset lifecycle — what landed, what's repointed, which PRs did it, what's queued next.</span></a>
<a class="card" href="audit.html"><b>Full audit →</b>
<span>Every data reference across the 8 repos: hosting patterns, registries, orphans, provenance, live-API analysis.</span></a>
<a class="card" href="{DL}/blob/main/CATALOG.md"><b>Dataset catalog ↗</b>
<span>The migrated-only registry generated from the manifests — class, license, integrity, consumers.</span></a>
</div>
"""
    body = f"""
<header class="doc">
<p class="eyebrow">QuantEcon · generated data audit · Python lecture family</p>
<h1>Lecture data — audit &amp; migration dashboard</h1>
<p class="meta">Every dataset referenced by lecture source across the 8 synced Python-family repos,
regenerated from each repo's <code>main</code> by
<a href="{DL}/blob/main/scripts/build_audit.py">a script</a> — not maintained by hand.
Companion to the migration of lecture data into
<a href="{DL}">QuantEcon/data-lectures</a>.</p>
<span id="freshness" class="freshness" data-generated="{esc(audit["generated"])}"
title="Rebuilt on every change to data-lectures and weekly on schedule — a badge older than a week means the scheduled rebuild has stopped.">
● generated {esc(audit["generated"])}</span>
<script>
(function () {{
  var el = document.getElementById('freshness');
  var gen = new Date(el.dataset.generated + 'T00:00:00Z');
  var days = Math.floor((Date.now() - gen.getTime()) / 86400000);
  if (isNaN(days)) return;
  var age = days <= 0 ? 'today' : days === 1 ? 'yesterday' : days + ' days ago';
  if (days > 14) {{
    el.classList.add('crit');
    el.textContent = '✗ stale — last updated ' + age + ' (' + el.dataset.generated + '); the scheduled rebuild has stopped';
  }} else if (days > 7) {{
    el.classList.add('warn');
    el.textContent = '⚠ last updated ' + age + ' (' + el.dataset.generated + ') — the weekly rebuild is overdue';
  }} else {{
    el.textContent = '● up to date — last updated ' + age + ' (' + el.dataset.generated + ')';
  }}
}})();
</script>
</header>
{tiles}
{migration_meter(audit)}
{cards}
{pattern_barlist(audit)}
{what_changed()}
"""
    return page("QuantEcon lecture data — audit & migration dashboard", "overview", body, audit)


# ---------------------------------------------------------------------------
# Page: migration tracker
# ---------------------------------------------------------------------------

# Reader-facing status labels — the dashboard is read by people who are not
# doing the migration, so the manifest speaks plainly; the lifecycle terms
# (pending/landed/repointed/final) appear only in the explained stepper detail.
STATUS_META = {
    # status → (pill css, label)
    "final": ("p-local", "✓ migrated"),
    "repointed": ("p-local", "✓ migrated"),
    "landed": ("p-own", "● copied, not yet switched"),
    "queued": ("p-legacy", "queued"),
    "unscheduled": ("p-embed", "not scheduled"),
}


def dataset_status(fname: str, migration: dict) -> tuple[str, str]:
    """→ (status, pilot) for any static dataset the audit sees. A record still
    at lifecycle `pending` reads as `queued` — same reader-facing meaning as a
    file named in a pending wave."""
    rec = (migration.get("datasets") or {}).get(fname)
    if rec:
        status = rec.get("status", "pending")
        return ("queued" if status == "pending" else status), rec.get("pilot", "")
    for wave in migration.get("pending") or []:
        if fname in (wave.get("datasets") or []):
            return "queued", wave.get("pilot", "")
    return "unscheduled", ""


STATUS_RANK = {"unscheduled": 0, "pending": 1, "queued": 1, "landed": 2,
               "repointed": 3, "final": 3}


def series_manifest(audit: dict) -> str:
    """Every static dataset with its migration status, grouped by the lecture
    series it belongs to — migrated files stay in the series they came FROM
    (green rows at the bottom of each group), so each group reads as that
    series' progress. A MIGRATED file consumed by two series appears in both
    groups; before migration a file has one home — the repo owning the bytes."""
    migration = audit["migration"] or {}
    manifests = audit["manifests"]
    groups: dict[str, list] = {}
    shared: dict[str, list] = {}
    for d in audit["datasets"]:
        home = repo_of_record(d)
        if home == "data-lectures":
            # migrated — list it where it was: under each series whose
            # lectures consume it (the manifest's consumers)
            homes = sorted({c["repo"].split("/")[-1]
                            for c in manifests.get(d["file"], {}).get("consumers", [])}) \
                    or [d["refs"][0]["repo"]]
            shared[d["file"]] = homes
            for h in homes:
                groups.setdefault(h, []).append(d)
        else:
            groups.setdefault(home, []).append(d)
    order = ["lecture-python-intro", "lecture-python-programming",
             "lecture-python.myst", "lecture-python-advanced.myst"]
    rows = ""
    for repo in [r for r in order if r in groups] + sorted(set(groups) - set(order)):
        ds = sorted(groups[repo],
                    key=lambda x: (STATUS_RANK.get(
                        dataset_status(x["file"], migration)[0], 0), x["file"]))
        statuses = [dataset_status(d["file"], migration)[0] for d in ds]
        n = len(ds)
        n_done = sum(1 for s in statuses if s in ("repointed", "final"))
        n_landed = statuses.count("landed")
        n_queued = statuses.count("queued")
        counts = [f"{n_done} migrated" if n_done else "",
                  f"{n_landed} copied, not switched" if n_landed else "",
                  f"{n_queued} queued" if n_queued else "",
                  f"{n - n_done - n_landed - n_queued} not scheduled"
                  if n - n_done - n_landed - n_queued else ""]
        pct = lambda k: max(0.8, 100 * k / n) if k else 0
        segs = ""
        if n_done:
            segs += f'<div class="seg a" style="width:{pct(n_done):.1f}%"></div>'
        if n_landed:
            segs += f'<div class="seg b" style="width:{pct(n_landed):.1f}%"></div>'
        rows += (f'<tr class="group"><td colspan="4">{esc(repo)} — '
                 f'{n} file{"s" if n != 1 else ""} · '
                 f'{esc(" · ".join(c for c in counts if c))}'
                 f'<div class="meter mini" role="img" aria-label="{n_done} of {n} migrated">{segs}</div>'
                 f'</td></tr>')
        for d, status_pilot in zip(ds, (dataset_status(d["file"], migration) for d in ds)):
            status, pilot = status_pilot
            css, label = STATUS_META.get(status, ("p-embed", status))
            if pilot and status == "queued":
                label += f" · wave {pilot}"
            migrated = status in ("repointed", "final")
            pills = " ".join(pattern_pill(p) for p in d["patterns"])
            if migrated:
                rec = (migration.get("datasets") or {}).get(d["file"]) or {}
                prior = rec.get("prior_pattern")
                if prior:
                    _, plabel, _ = PATTERN_META.get(prior, ("", prior, ""))
                    pills += f'<div class="note">was: {esc(plabel)}</div>'
                others = [h.replace("lecture-", "") for h in shared.get(d["file"], [])
                          if h != repo]
                if others:
                    pills += (f'<div class="note">shared — also listed under '
                              f'{esc(", ".join(others))}</div>')
            rows += (f'<tr{" class=\"row-migrated\"" if migrated else ""}>'
                     f'<td class="mono">{esc(d["file"])}</td>'
                     f'<td class="note">{esc(d["description"])}</td>'
                     f'<td>{pills}</td>'
                     f'<td><span class="pill {css}">{esc(label)}</span></td></tr>')
    return f"""
<h2>All datasets by series</h2>
<p class="lede">Every static file the lectures read, grouped by the lecture series it belongs
to. Migrated files stay listed in the series they came from — the green rows at the bottom of
each group — so each group reads as that series' progress. A migrated file consumed by two
series appears in both groups (marked <em>shared</em>); the tiles above count distinct files.
<em>Not scheduled</em> means no milestone has claimed the file yet; the broad sweep (see the
milestones below) eventually covers them all. Data written by the lectures themselves and
live-API reads are not migration targets and are tracked on the
<a href="audit.html">audit page</a>.</p>
<div class="tablewrap"><table>
<tr><th>File</th><th>Contents</th><th>Hosting today</th><th>Status</th></tr>
{rows}
</table></div>
"""


def stepper(fname: str, rec: dict, verified: bool) -> str:
    status = rec.get("status", "pending")
    if status not in STATUS_STEPS:
        raise SystemExit(
            f"migration.yml: unknown status {status!r} for {fname} — expected one of "
            f"{', '.join(STATUS_STEPS)} (the strict scan flags this too; run "
            f"build_audit.py scan --strict)")
    reached = STATUS_STEPS.index(status)
    detail = {
        "pending": "",
        "landed": pr_link(str((rec.get("landed") or {}).get("pr", ""))) +
                  f'<br>{esc((rec.get("landed") or {}).get("date", ""))}',
        "repointed": "<br>".join(pr_link(str(r.get("pr", ""))) for r in rec.get("repoints") or []),
        "final": ("awaits " + issue_link("QuantEcon/data-lectures#15")) if status != "final"
                 else esc((rec.get("cutover") or {}).get("date", "")),
    }
    steps = ""
    for i, name in enumerate(STATUS_STEPS):
        cls = "done" if i <= reached else ("next" if i == reached + 1 else "")
        steps += (f'<div class="step {cls}"><div class="dot"></div>'
                  f'<div class="slbl">{name}</div>'
                  f'<div class="sdetail">{detail.get(name, "")}</div></div>')
    check = ('<span class="flag ok" title="the scan confirms every consumer reads data-lectures">✓ verified against today\'s scan</span>'
             if verified else
             '<span class="flag crit">✗ scan disagrees with this status</span>')
    return f'<div class="steps">{steps}</div><p class="note" style="margin-bottom:0">{check}</p>'


def milestones(audit: dict) -> str:
    """The migration programme as reader-facing milestones — completed waves
    (derived from migration.yml records), upcoming waves, the broad sweep, and
    the final-URL switch. This section is what lets the rest of the dashboard
    stay plan-agnostic: wave codes like P3 mean something only because they
    are presented here."""
    mig = audit["migration"] or {}
    recs = mig.get("datasets") or {}
    manifests = audit["manifests"]

    by_pilot: dict[str, list] = {}
    for fname, rec in recs.items():
        by_pilot.setdefault(rec.get("pilot", "?"), []).append((fname, rec))
    items = ""
    for pilot in sorted(by_pilot):
        entries = by_pilot[pilot]
        files = sorted(f for f, _ in entries)
        done = all(r.get("status") in ("repointed", "final") for _, r in entries)
        dates = [str((r.get("repoints") or [{}])[-1].get("date", "")) for _, r in entries]
        series = {c["repo"] for f, _ in entries
                  for c in (manifests.get(f, {}).get("consumers") or [])}
        n_series = len(series)
        mark, cls = ("✓", "ok") if done else ("○", "")
        items += f"""
<div class="finding {cls}">
<b>{mark} Wave {esc(pilot)} — {len(files)} dataset{"s" if len(files) != 1 else ""},
consumed by {n_series} lecture series{" — completed " + esc(max(dates)) if done and max(dates) else ""}</b>
<p>{" · ".join(f"<code>{esc(f)}</code>" for f in files)}</p>
</div>
"""
    for w in mig.get("pending") or []:
        files = w.get("datasets") or []
        flist = (" · ".join(f"<code>{esc(f)}</code>" for f in sorted(files))
                 if files else "produces new snapshot files here; no existing file moves")
        tracking = " · ".join(issue_link(t) for t in w.get("tracking") or [])
        items += f"""
<div class="finding">
<b>○ Wave {esc(w.get("pilot", ""))} — {esc(w.get("title", w.get("scope", "")))}</b>
<p>{flist}</p>
<p>Tracking: {tracking}</p>
</div>
"""
    n_unsched = sum(1 for d in audit["datasets"]
                    if dataset_status(d["file"], mig)[0] == "unscheduled")
    items += f"""
<div class="finding">
<b>○ Broad sweep — every remaining static file</b>
<p>The {n_unsched} not-yet-scheduled files move once the waves above have proven the
process for each kind of data. Mechanical from there: one data PR here, one switch PR
per consuming lecture repo.</p>
</div>
<div class="finding">
<b>○ Final URLs — serve everything from <code>data.quantecon.org</code></b>
<p>Migrated lectures currently read this repository's GitHub URL. Once the custom domain
is live, every migrated dataset switches to its permanent
<code>data.quantecon.org/lectures/…</code> address in a single sweep
({issue_link("QuantEcon/data-lectures#15")}). No dataset has made this step yet.</p>
</div>
"""
    return f"""
<h2>Milestones</h2>
<p class="lede">The migration proceeds in small waves, each proving the process for a harder
kind of data before the broad sweep moves the rest.</p>
{items}
"""


def render_migration(audit: dict) -> str:
    mig = audit["migration"] or {}
    recs = mig.get("datasets") or {}
    manifests = audit["manifests"]
    by_name = {d["file"]: d for d in audit["datasets"]}

    pipelines = ""
    for fname, rec in recs.items():
        d = by_name.get(fname)
        verified = bool(d and d["fully_migrated"]) if rec.get("status") in ("repointed", "final") else True
        m = manifests.get(fname, {})
        consumers = ", ".join(
            lecture_link(c["repo"].split("/")[-1], c["file"], f'{c["repo"].split("/")[-1]} · {Path(c["file"]).stem}')
            for c in m.get("consumers", []))
        prior = rec.get("prior_pattern", "")
        pipelines += f"""
<div class="pipeline">
<div class="head">
<span class="name mono">{esc(fname)}</span>
<span class="pill p-dl">wave {esc(rec.get("pilot", ""))}</span>
{pattern_pill(prior)} <span class="note">→</span> {pattern_pill("data-lectures")}
<span class="note" style="margin-left:auto"><a href="{RAW}/{esc(fname)}">file</a> ·
<a href="{DL}/blob/main/lectures/{esc(fname)}.yml">manifest</a></span>
</div>
<p class="note" style="margin:0 0 10px">{esc(m.get("title", ""))} — consumed by {consumers or "—"}</p>
{stepper(fname, rec, verified)}
</div>
"""

    problems = audit["problems"]["migration_inconsistencies"]
    consistency = ('<div class="finding ok"><b>Consistency check: clean.</b>'
                   '<p>The tracker, the dataset manifests and today\'s scan of every lecture repo agree.</p></div>'
                   if not problems else
                   '<div class="finding crit"><b>Consistency check: FAILING.</b><ul>'
                   + "".join(f"<li>{esc(p)}</li>" for p in problems) + "</ul></div>")

    n_re = sum(1 for r in recs.values() if r.get("status") in ("repointed", "final"))
    queued = {f for w in (mig.get("pending") or []) for f in w.get("datasets") or []}
    n_unsched = sum(1 for d in audit["datasets"]
                    if dataset_status(d["file"], mig)[0] == "unscheduled")
    body = f"""
<header class="doc">
<p class="eyebrow">Migration tracker · generated and verified on every build</p>
<h1>Moving lecture data into one central repository</h1>
<p class="meta">The QuantEcon lectures read data from many places — their own repos, local
files, retired repos, live APIs. This tracker shows the move to a single canonical home
(<a href="{DL}">data-lectures</a>): what has moved, what's next, and how far along it is.
Every status is verified against a fresh scan of the lecture repos, so this page cannot
claim a migration that didn't happen.</p>
</header>
<div class="stats">
<div class="stat ok"><b>{n_re}</b><span>datasets migrated — every consuming lecture reads the central copy</span></div>
<div class="stat"><b>{len(queued)}</b><span>queued for the next waves</span></div>
<div class="stat"><b>{n_unsched}</b><span>not yet scheduled (the broad sweep)</span></div>
</div>
<h3>How a dataset moves</h3>
<p><b>pending</b> — identified for migration; nothing has moved yet.
<b>landed</b> — the file and its metadata are merged into the central repo; lectures unchanged.
<b>repointed</b> — every consuming lecture now reads the central copy (shown as
<em>✓ migrated</em> in the table below).
<b>final</b> — the lecture reads the permanent <code>data.quantecon.org</code> address
(the last milestone below).</p>
{consistency}
{series_manifest(audit)}
{milestones(audit)}
<h2>Migration record — dataset by dataset</h2>
<p class="lede">The full provenance for each migrated dataset: which pull requests landed the
data and switched each consuming lecture, and where it sits in the lifecycle.</p>
{pipelines}
"""
    return page("Migration tracker — data-lectures", "migration", body, audit)


# ---------------------------------------------------------------------------
# Page: full audit
# ---------------------------------------------------------------------------

def repo_of_record(d: dict) -> str:
    """Group a dataset under the repo that owns the bytes being read."""
    for r in d["refs"]:
        if r["pattern"] in ("own-repo", "local-path"):
            return r["repo"]
        if r["pattern"] == "sibling":
            return r["gh_repo"]
    if d["migrated"]:
        return "data-lectures"
    return d["refs"][0]["repo"]


def audit_registry_a(audit: dict) -> str:
    groups: dict[str, list] = {}
    for d in audit["datasets"]:
        groups.setdefault(repo_of_record(d), []).append(d)
    order = ["data-lectures", "lecture-python-intro", "lecture-python-programming",
             "lecture-python.myst", "lecture-python-advanced.myst"]
    rows = ""
    for repo in [r for r in order if r in groups] + sorted(set(groups) - set(order)):
        ds = groups[repo]
        rows += f'<tr class="group"><td colspan="5">{esc(repo)} — {len(ds)} files</td></tr>'
        for d in sorted(ds, key=lambda x: x["file"]):
            lecture_list = ", ".join(sorted({
                f'{r["lecture"]}' + (" (wasm)" if r["repo"] == "lecture-wasm" else "")
                for r in d["refs"]}))
            pills = " ".join(pattern_pill(p) for p in d["patterns"])
            flags = []
            if "local-path" in d["patterns"]:
                flags.append('<span class="flag">⚠ breaks in Colab/notebook download</span>')
            if any(r.get("lfs_media") for r in d["refs"]):
                flags.append('<span class="note">via media.githubusercontent (LFS)</span>')
            if any(r.get("branch_pinned") for r in d["refs"]):
                flags.append('<span class="flag crit">✗ pinned to a non-default branch</span>')
            if "new-since-2026-07-15" in d.get("flags", []):
                flags.append('<span class="flag">new since the 2026-07-15 audit</span>')
            if "lectures-root" in d.get("flags", []):
                flags.append('<span class="note">lives at lectures/ root</span>')
            if d["fully_migrated"]:
                flags.append('<span class="flag ok">✓ migrated</span>')
            note = d.get("note", "")
            if note:
                flags.append(f'<span class="note">{esc(note)}</span>')
            rows += (f'<tr><td class="mono">{esc(d["file"])}</td>'
                     f'<td>{esc(d["description"])}</td>'
                     f'<td>{esc(lecture_list)}</td>'
                     f'<td>{pills}</td>'
                     f'<td>{" ".join(flags)}</td></tr>')
    return f"""
<h2><span class="sec">2</span>Registry A — static dataset files ({len(audit["datasets"])})</h2>
<p class="lede">Every distinct file a lecture reads, grouped by the repo that owns the bytes.
lecture-wasm mirrors intro's lectures and reads intro's copies by URL, so it appears as a
consumer, not an owner.</p>
<div class="tablewrap"><table>
<tr><th>File</th><th>Contents</th><th>Lecture(s)</th><th>Hosting</th><th>Flags / notes</th></tr>
{rows}
</table></div>
"""


def audit_patterns(audit: dict) -> str:
    counts: dict[str, dict] = {}
    for d in audit["datasets"]:
        for r in d["refs"]:
            c = counts.setdefault(r["pattern"], {"n": 0, "repos": set()})
            c["n"] += 1
            c["repos"].add(r["repo"].replace("lecture-python-", "").replace("lecture-", ""))
    counts.setdefault("embedded", {"n": len(audit["embedded"]), "repos": {
        e["repo"].replace("lecture-python-", "").replace("lecture-", "") for e in audit["embedded"]}})
    api_lects = {(u["repo"], u["lecture"]) for u in audit["api"]}
    counts.setdefault("api", {"n": len(api_lects), "repos": {
        r.replace("lecture-python-", "").replace("lecture-", "") for r, _ in api_lects}})
    rows = ""
    for key, (css, label, desc) in PATTERN_META.items():
        if key not in counts:
            continue
        c = counts[key]
        unit = " lectures" if key == "api" else ""
        rows += (f'<tr><td>{pattern_pill(key)}</td><td>{esc(desc)}</td>'
                 f'<td class="num">{c["n"]}{unit}</td>'
                 f'<td class="note">{esc(", ".join(sorted(c["repos"])))}</td></tr>')

    forms = sorted({r["url_form"] for d in audit["datasets"] for r in d["refs"] if r.get("url_form")})
    form_list = "".join(f'<li class="mono" style="font-size:13px">{esc(f)}</li>' for f in forms)
    return f"""
<h2><span class="sec">1</span>Hosting patterns in use</h2>
<p class="lede">Eight distinct patterns. The 2026-07-15 audit found seven; adding lecture-wasm
surfaced the <em>sibling repo URL</em> pattern, and the migration added <em>data-lectures</em>
while retiring <em>legacy-repo URL</em> entirely.</p>
<div class="tablewrap"><table>
<tr><th>Pattern</th><th>What it looks like</th><th>Refs</th><th>Where</th></tr>
{rows}
</table></div>
<h3>{len(forms)} URL spellings for "raw file on GitHub"</h3>
<ul>{form_list}</ul>
<p class="note">Down from six — the <code>blob/master…?raw=true</code> spelling retired with the
legacy-repo refs. One canonical spelling is a styleguide question for
{issue_link("QuantEcon/QuantEcon.manual#108")}.</p>
"""


def audit_registry_b(audit: dict) -> str:
    by_file: dict[str, list] = {}
    for e in audit["embedded"]:
        by_file.setdefault(e["file"], []).append(e)
    rows = ""
    for fname, uses in sorted(by_file.items()):
        series = " · ".join(sorted({u["repo"].replace("lecture-python-", "").replace("lecture-", "")
                                    for u in uses}))
        lects = ", ".join(sorted({u["lecture"] for u in uses}))
        multi = ('<span class="flag">— same data maintained in '
                 f'{len({u["repo"] for u in uses})} repos</span>'
                 if len({u["repo"] for u in uses}) > 1 else "")
        rows += (f'<tr><td class="mono">{esc(fname)}</td><td>{esc(lects)}</td>'
                 f'<td>{esc(series)} {multi}</td></tr>')
    return f"""
<h2><span class="sec">3</span>Registry B — data embedded in lecture source ({len(by_file)} files)</h2>
<p class="lede">Written to the working directory by the lecture itself (<code>%%file</code>,
<code>%%writefile</code>, or an in-lecture <code>open(…, 'w')</code>), then read back.
Self-contained everywhere — including Colab — at the cost of data living inside narrative source.</p>
<div class="tablewrap"><table>
<tr><th>File</th><th>Lecture(s)</th><th>Series</th></tr>
{rows}
</table></div>
"""


def audit_registry_c(audit: dict) -> str:
    rows = ""
    for u in sorted(audit["api"], key=lambda x: (x["provider"], x["repo"], x["lecture"])):
        repo_short = u["repo"].replace("lecture-python-", "").replace("lecture-", "")
        ped = pill(PEDAGOGY_META, u["pedagogy"]) if u.get("pedagogy") else ""
        note = f'<div class="note">{esc(u["note"])}</div>' if u.get("note") else ""
        rows += (f'<tr><td><span class="pill p-api">{esc(u["provider"])}</span> '
                 f'<span class="note">{esc(u["access"])}</span></td>'
                 f'<td class="mono">{esc(u["series"])}</td>'
                 f'<td>{esc(u["lecture"])}</td><td>{esc(repo_short)}</td>'
                 f'<td>{ped}{note}</td></tr>')
    n_lects = len({(u["repo"], u["lecture"]) for u in audit["api"]})
    return f"""
<h2><span class="sec">4</span>Registry C — live API data ({n_lects} lectures)</h2>
<p class="lede">Fetched at build time from third-party services — the build-reproducibility
surface, and the blocker for the WASM/JupyterLite target (pyodide cannot reach most of these
APIs; that is lecture-wasm's core problem, {issue_link("QuantEcon/meta#143")}).</p>
<div class="tablewrap"><table>
<tr><th>Provider / access</th><th>Series or tickers</th><th>Lecture</th><th>Series</th><th>Why live</th></tr>
{rows}
</table></div>
<div class="legend">
<span class="key">{pill(PEDAGOGY_META, "lesson")} the fetch workflow is the teaching point — keep live</span>
<span class="key">{pill(PEDAGOGY_META, "mixed")} discovery is taught, plots could read a snapshot</span>
<span class="key">{pill(PEDAGOGY_META, "incidental")} just needs a series — snapshot-ready</span>
</div>
"""


def audit_reuse(audit: dict) -> str:
    rows = ""
    for d in audit["datasets"]:
        repos = {c[0] for c in d["consumers"]}
        if len(repos) > 1:
            series = " + ".join(sorted(r.replace("lecture-python-", "").replace("lecture-", "")
                                       for r in repos))
            how = ("all consumers read data-lectures — the target state"
                   if d["fully_migrated"] else
                   "wasm mirrors intro and reads intro's copy by URL"
                   if "lecture-wasm" in repos else "")
            rows += (f'<tr><td class="mono">{esc(d["file"])}</td><td>{esc(series)}</td>'
                     f'<td class="note">{esc(how)}</td></tr>')
    multi_embed = ""
    by_file: dict[str, set] = {}
    for e in audit["embedded"]:
        by_file.setdefault(e["file"], set()).add(e["repo"])
    for fname, repos in sorted(by_file.items()):
        if len(repos) > 1:
            series = " + ".join(sorted(r.replace("lecture-python-", "").replace("lecture-", "")
                                       for r in repos))
            multi_embed += (f'<tr><td class="mono">{esc(fname)}</td><td>{esc(series)}</td>'
                            f'<td class="note">duplicated as %%file blocks — {len(repos)} copies '
                            f'of the same data to keep in sync</td></tr>')
    return f"""
<h2><span class="sec">5</span>Cross-series reuse</h2>
<p class="lede">Files consumed by more than one repo. Before the migration the only true
cross-series files were the pandas_panel trio; the wasm mirror now multiplies every intro
dataset into a second consumer.</p>
<div class="tablewrap"><table>
<tr><th>Dataset</th><th>Consumers</th><th>How it's shared today</th></tr>
{rows}{multi_embed}
</table></div>
"""


def audit_orphans(audit: dict) -> str:
    rows = ""
    cur = None
    for o in audit["orphans"]:
        if o["repo"] != cur:
            cur = o["repo"]
            n = sum(1 for x in audit["orphans"] if x["repo"] == cur)
            rows += f'<tr class="group"><td colspan="3">{esc(cur)} — {n} files</td></tr>'
        rows += (f'<tr><td class="mono">{esc(o["path"])}</td>'
                 f'<td>{pill(ORPHAN_KIND, o["kind"])}</td>'
                 f'<td class="note">{esc(o["note"])}</td></tr>')
    return f"""
<h2><span class="sec">6</span>Committed but unreferenced data files ({len(audit["orphans"])})</h2>
<p class="lede">Files in a repo's tree that no executed code cell reads. Orphan-sweep candidates
are tracked in {issue_link("QuantEcon/meta#337")}; <em>shadowed</em> and <em>exercise-download</em>
files are functional, just invisible to a URL-level audit.</p>
<div class="legend">
<span class="key">{pill(ORPHAN_KIND, "orphan")} dead weight — nothing reads it</span>
<span class="key">{pill(ORPHAN_KIND, "shadowed")} a %%file cell regenerates it at build time</span>
<span class="key">{pill(ORPHAN_KIND, "mirror-orphan")} wasm copy; the wasm lecture reads intro's URL</span>
<span class="key">{pill(ORPHAN_KIND, "exercise-download")} prose link target — referenced, not by code</span>
</div>
<div class="tablewrap"><table>
<tr><th>File</th><th>State</th><th>Why</th></tr>
{rows}
</table></div>
"""


def provenance_key(d: dict, manifests: dict) -> str:
    """Canonical provenance class. Manifests use verbatim/constructed/dynamic
    snapshot plus builder_status; a constructed dataset whose builder was never
    recovered stays visible as pipeline-lost (AGENTS.md: that gap is a tracked
    bug, not a resolved one)."""
    p = d["provenance"] or "?"
    if d["manifest"]:
        m = manifests.get(d["file"]) or {}
        if p in ("constructed", "dynamic snapshot"):
            return ("constructed-lost" if m.get("builder_status") == "unrecovered"
                    else "constructed-committed")
    return p


def audit_provenance(audit: dict) -> str:
    counts: dict[str, int] = {}
    for d in audit["datasets"]:
        key = provenance_key(d, audit["manifests"])
        counts[key] = counts.get(key, 0) + 1
    tiles = ""
    tone = {"constructed-lost": " warn", "author-assembled": " warn"}
    for key, (css, label, desc) in PROVENANCE_META.items():
        if key in counts:
            tiles += (f'<div class="stat{tone.get(key, "")}"><b>{counts[key]}</b>'
                      f'<span>{esc(label)} — {esc(desc)}</span></div>')
    rows = ""
    for key, (css, label, desc) in PROVENANCE_META.items():
        ds = [d for d in audit["datasets"]
              if provenance_key(d, audit["manifests"]) == key]
        if not ds:
            continue
        rows += f'<tr class="group"><td colspan="3">{esc(label)} — {len(ds)}</td></tr>'
        for d in sorted(ds, key=lambda x: x["file"]):
            src = ("manifest" if d["manifest"] else "audit annotation")
            rows += (f'<tr><td class="mono">{esc(d["file"])}</td>'
                     f'<td class="note">{esc(d.get("note") or d["description"])}</td>'
                     f'<td class="note">{esc(src)}</td></tr>')
    return f"""
<h2><span class="sec">7</span>Provenance — how each file came to exist</h2>
<p class="lede">The axis the manifest convention formalizes (verbatim / constructed / dynamic
snapshot, {issue_link("QuantEcon/meta#336")}). For migrated datasets this comes from their
manifests; for everything else, from the curated audit annotations.</p>
<div class="stats">{tiles}</div>
<div class="tablewrap"><table>
<tr><th>File</th><th>Provenance</th><th>Recorded in</th></tr>
{rows}
</table></div>
"""


def audit_rules() -> str:
    rules = [
        ("Default to snapshots.",
         "A lecture reads data from a stable snapshot URL (data-lectures). Live API calls are "
         "the exception and require a reason recorded in the lecture source."),
        ("Live APIs are for teaching data access, not for getting data.",
         "A live call is justified when the fetch workflow is itself the lesson (the pandas "
         "lecture's wbgapi/yfinance sections) or when currency is the point. “The lecture "
         "needs series X” is not a reason — that's what snapshots are for."),
        ("Every live-API lecture gets a snapshot twin.",
         "A refresh builder in data-lectures producing the snapshot (the business_cycle_data.csv "
         "pattern, already prototyped). Breakage becomes a one-line URL switch, and the WASM "
         "build always uses the twin — pyodide cannot reach the live APIs at all."),
        ("Prefer direct CSV endpoints over wrapper libraries.",
         "Where live access stays, fredgraph.csv-style URLs beat pandas_datareader-style "
         "wrappers: one less dependency, and the git history shows the wrappers are what broke."),
        ("Snapshots carry provenance metadata.",
         "Source, series IDs, retrieval date, license and refresh cadence — the manifest schema "
         "in this repo is the template; the provenance classes in §7 say which fields are "
         "required."),
    ]
    findings = "".join(f'<div class="finding"><b>{i}. {esc(t)}</b><p>{esc(b)}</p></div>'
                       for i, (t, b) in enumerate(rules, 1))
    return f"""
<h2><span class="sec">8</span>Draft rules for <code>styleguide/datasets.md</code></h2>
<p class="lede">Distilled from the live-API pedagogy analysis (§4) and the migration pilots;
feeding {issue_link("QuantEcon/QuantEcon.manual#108")}.</p>
{findings}
"""


def render_audit_page(audit: dict) -> str:
    s = audit["stats"]
    body = f"""
<header class="doc">
<p class="eyebrow">Full audit · regenerated from each repo's <code>main</code></p>
<h1>Dataset registry — Python lecture family</h1>
<p class="meta">Every dataset referenced by lecture source across the 8 synced repos.
The successor to the hand-built {PREV_SNAPSHOT} audit — same taxonomy, now generated.</p>
</header>
<div class="stats">
<div class="stat"><b>{s["static_files"]}</b><span>distinct static data files referenced</span></div>
<div class="stat"><b>{s["committed_files"]}</b><span>data files committed across the repos</span></div>
<div class="stat warn"><b>{s["orphans"]}</b><span>committed files no code cell references</span></div>
<div class="stat ok"><b>{s["legacy_refs"]}</b><span>legacy-repo URLs (8 on {PREV_SNAPSHOT})</span></div>
<div class="stat"><b>{s["api_lectures"]}</b><span>lectures fetching live API data</span></div>
<div class="stat ok"><b>{s["migrated"]}</b><span>datasets fully migrated to data-lectures</span></div>
</div>
{audit_patterns(audit)}
{audit_registry_a(audit)}
{audit_registry_b(audit)}
{audit_registry_c(audit)}
{audit_reuse(audit)}
{audit_orphans(audit)}
{audit_provenance(audit)}
{audit_rules()}
"""
    return page("Full data audit — Python lecture family", "audit", body, audit)


def render(audit: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_index(audit), encoding="utf-8")
    (out_dir / "migration.html").write_text(render_migration(audit), encoding="utf-8")
    (out_dir / "audit.html").write_text(render_audit_page(audit), encoding="utf-8")
