# PLAN — `qeld`, the consumer-side data package

**Status:** design settled, nothing implemented · **Last updated:** 2026-08-10
**Relationship to `PLAN.md`:** that document migrates *bytes* into this repo. This one gives *consumers* a
stable way to read them. They are independent — the migration completes with or without `qeld` — but the
call-site convention here replaces repoint rules 5–6 for any lecture that adopts it.

---

## 1. What `qeld` is

A tiny package that hands a lecture a **context-aware URL** for a published dataset. The lecture then reads
it with pandas, in the open:

```python
url  = qeld.url('mpd2020.xlsx')                      # or inline, see §4.1
data = pd.read_excel(url, sheet_name='Full data')
```

**Purpose: transit assistance and simplified fetching.** Not data management — data history is git's job.

It exists to solve three concrete problems:

1. **The host is spelled six ways.** The same lecture reads the same file via
   `github.com/…/raw/main/…` in `lecture-python-intro` and `raw.githubusercontent.com/…` in `lecture-wasm`,
   because the first fails CORS in the browser. That split *is* repoint rules 5–6. `qeld.url()` erases it.
2. **`pyodide_http.patch_all()` is in every wasm lecture.** Importing `qeld` under emscripten installs the
   transport shim, and those two lines leave the lectures.
3. **The host cutover.** When `data.quantecon.org` lands (#37, #15), it is one constant in one package
   rather than an edit in every lecture.

**What it is not:** a cache, a fetcher, a loader, a data-version manager, or an integrity client. See §3.1.

---

## 2. Decisions

D1–D5 were taken 2026-08-10 against the original design report. D2, D3 and D5 were **revised the same day**
in a working session that re-scoped the package from fetch-and-cache to URL-resolver; D1 and D4 stand
unchanged. D6–D10 are new.

| # | decision | status |
|---|---|---|
| **D1** | Name `qeld`. Free on PyPI (verified 2026-08-10; `quantecon-data` also free, `qeds` is taken and still installable at 0.7.0) | unchanged |
| **D2** | **Call style: `qeld.url()` substituted in place of the URL expression the lecture already uses.** No `fetch()`, no `load()` | **revised** — see §4.1 |
| **D3** | **Pin policy: semver, `qeld>=1,<2` in install cells; `==` in env files if lockfile determinism is wanted.** CalVer retired | **revised** — see §3.4 |
| **D4** | Home: in-repo `packages/qeld/`. Bytes, manifest and package in one commit | unchanged |
| **D5** | v1 scope: `url()` and `info()` only. Non-goals: live APIs (#26), Julia, datascience/networks, mirrors, a MyST provenance directive | **narrowed** |
| **D6** | **Context detection may change transport; never semantics** | new — §3.2 |
| **D7** | **Catalog bundled in the wheel, advisory not authoritative** | new — §3.3 |
| **D8** | **Data format: tier 1 binds at intake, tier 2 is a forward-looking preference** | new — §4.2 |
| **D9** | **Integrity lives in CI, not at the call site** | new — §6 |
| **D10** | **Rollout is ordered by win, not by migration track** | new — §7 |

**The scoping principle throughout:** ship the minimum; add sophistication as demand requires.

### 2.1 Why D3 changed — the `qbn` precedent does not transfer

The original rationale for exact CalVer pins was "the `qbn==1.6` house pattern for data packages". It fails
on inspection, and the reasoning is recorded here so it is not re-proposed:

- `quantecon_book_networks` ships its data **inside the wheel** (`data.py:1-16`, `importlib.resources`). Its
  pin is immortal because nothing is fetched. `qeld` inverts that exactly.
- As a house pattern it does not generalise: of `lecture-python-intro`'s 16 install cells, the **only** exact
  pins are the two `qbn` cells; `quantecon` itself is unpinned in five. `lecture-wasm` pins nothing.
- "The pin names the data vintage" is a category error. The serving tree holds one version per filename, so
  a version pins the **key → URL contract**, never the bytes.

**What `<2` protects, and therefore what the major version means:** catalog keys are append-only, and a
key's meaning never changes within a major version.

---

## 3. Design

### 3.1 API surface — two functions

| call | returns | notes |
|---|---|---|
| `qeld.url(name)` | `str` | the context-correct URL. Unknown key → **warning with near-key suggestions, still returns a URL** |
| `qeld.info(name)` | provenance record | title, source, licence, citation, `citation_policy`, `redistribution`, `sha256`. Offline, from the bundled catalog |

`info()` earns its place because Maddison's `citation_policy` is a live obligation a lecture must discharge,
and the manifest already carries it.

**No `fetch()`, `load()`, `open()`, cache, or path.** The full static corpus is reachable with `url()` alone
once the format convention (§4.2) is applied — see §5.3.

### 3.2 Context detection (D6)

**The rule: context may change transport; it may never change semantics.** Same key, same bytes, same result
everywhere. A design where context changes *what you get* produces "works in my notebook, fails in CI".

Exactly two jobs:

1. **URL form** — `raw.githubusercontent.com` under Pyodide (the `github.com/…/raw/` form 302s and fails
   CORS); the 302-tolerant form elsewhere; `data.quantecon.org` for both after #37.
2. **Browser transport shim** — under emscripten, `import qeld` installs the fetch shim, because the right
   URL is still not enough: `pd.read_excel(url)` goes through urllib, which fails in the browser.

Explicitly **not** detection's job: caching, fallback hosts, graceful degradation on fetch failure.

### 3.3 Catalog (D7)

`url()` does not need a catalog to *resolve* — keys are filenames and the tree is flat, so the URL is
`base + name`. The catalog exists to validate a key and to answer `info()`.

- **Bundled in the wheel, advisory not authoritative.** Unknown key → warning + near-key suggestions, and the
  URL is still returned; the subsequent 404 confirms it.
- **Why bundled:** typo diagnosis is the common failure and `qeld` cannot catch it after the fact — pandas
  does the fetch, so a bad key surfaces as a pandas 404 that never mentions `qeld`. Keys carry extensions and
  the repo serves both `longprices.xls` and `mpd2020.xlsx`, so `.xls`/`.xlsx` confusion is live.
- **Why advisory:** fail-open means a dataset that landed after your wheel still works. **No new dataset ever
  requires a package release.**
- **One compiler, three outputs.** `scripts/build_catalog.py` already emits `CATALOG.md`; it gains
  `catalog.json` for the wheel, sharing a freshness gate. This is the CI that PLAN Phase 2 promised.
- **Rejected, on the record:** a catalog-free package (`url()` = `base + name`, `info()` fetching the served
  sidecar — the sidecars *are* served, `text/yaml`, `acao: *`). Attractive because the package would only
  change when its code changes, but it gives up the one diagnostic that matters day to day.

### 3.4 Versioning and pinning (D3)

- **Semver**, frozen at 1.0 after the first pilots pass.
- **Install cells: `qeld>=1,<2`.** Install cells resolve fresh every session (Colab, Binder, wasm/piplite),
  so a corrected release is picked up automatically.
- **Env files: `==` if wanted.** These are resolved once and cached, so a maintainer is present to act on a
  break.
- **A byte correction behaves as `AGENTS.md` already intends:** same filename, same URL, every consumer gets
  the fix, nothing breaks.

### 3.5 Zero runtime dependencies

Pure `py3-none-any` wheel, stdlib only, so one artifact serves CPython, Colab and Pyodide via
micropip/piplite. `info()` reads the bundled catalog with `json` — no YAML parser at runtime.

---

## 4. Conventions this creates

### 4.1 The call-site rule (D2) — substitute in place

> Lecture code reads published data through `qeld.url('<filename>')`, substituted **in place of the URL
> expression the lecture already uses** — an inline literal becomes an inline call, an assigned variable
> keeps its assignment. The reader (`pd.read_*`, `pl.read_*`, …) and all its kwargs stay visible and
> unchanged.

Chosen by testing three candidates against every idiom in the corpus (§5). Inline-always destroys reused
variables across 47 sites; two-step-always turns one line into two across 18 inline literals. Substitute-in-
place is the only form that wins everywhere, and it has the property that matters for a ~78-site sweep:

**The diff is always and only the URL expression**, so a reviewer verifies a migration PR by reading the
changed lines alone. It satisfies the maintainer's bar — *"no more complex than it currently is just fetching
a url"* — by construction, since the lecture's shape is unchanged.

The install cell is **accepted cost**, not added complexity. This answers #58's stated objection by decision
rather than by design.

**Carve-outs — do not convert:**

| carve-out | why | sites |
|---|---|---|
| Live parameterised API endpoints | `url()` keys bare filenames and cannot express a query string; in `pandas.md` the raw URL is the *subject* of a teaching section | 4 |
| Reads whose literal URL **is the lesson** | `pandas_panel` prose reads *"The dataset can be accessed with the following link:"* then shows it. All three files already resolve to data-lectures in the form `qeld` emits, so there is no gain to offset it | 3 |
| Reads whose file is also named by a prose/`{download}` link | `url()` cannot appear in markdown; converting the code alone leaves two spellings that drift | 3, until §8.2 |

### 4.2 Data format (D8)

> **Tier 1 (binding, at intake):** a published dataset ships in a format its consumer can read **directly
> from a URL**.
> **Tier 2 (preference, forward-looking):** where the format is *not itself part of what is being taught*,
> prefer text.

Tier 1 binds — stricter than the house pattern elsewhere ("licensing does not gate migration"), deliberately:
a missing licence field is a gap you record, whereas a non-URL-readable format produces a lecture a reader
cannot run. Every file failing tier 1 today is read from a **bare local path** — the Colab breakage the
programme exists to retire. Enforceable from the catalog alone: assert every catalogued extension is on the
readable list.

Tier 2's test is *"is the format the lesson?"*, not *"does the format carry information?"* — `.dta` carries
no information beyond its values, but `pd.read_stata` **is** the lesson in `ols.md`, so it is never
converted.

### 4.3 CSV conversion is lossless in the file, not on read

Verified 2026-08-10. `to_csv` writes shortest-round-trip repr, but **pandas' default CSV parser is fast, not
correctly rounded.** On `dataBHS.mat` → CSV: default `float_precision='high'` differs in 18 of 708 values
(max relative error 2.1e-16); `'legacy'` differs in 164; `'round_trip'` is bit-exact.

So any binary→text conversion must **state its read**, and its gate must run `np.array_equal` **under the
reader the lecture will actually use**. 2.1e-16 is immaterial to a figure, but PLAN rule 4's discipline is
"provably cannot change output", and this is the difference between provable and negligible.

---

## 5. The call-site audit — input to the package

**Snapshot: 2026-08-10**, six repos, 40 lectures, 115 read sites. Machine-readable worklist:
`scripts/qeld_callsites.yml`. **Regenerate before the sweep** — `lecture-python-intro` and this repo both
moved during the session that produced it.

### 5.1 The unit of work is ~78 URL definitions, not 115 reads

23 of the 115 sites are downstream uses of a variable assigned earlier (`pd.read_excel(data_url, …)`).
`french_rev` reads `dette_url` six times. One `qeld.url()` call serves N reads — which is why the call-site
rule preserves variables.

| idiom | definitions | notes |
|---|---:|---|
| A — split string literal across lines | 23 | the clearest win; `polars.md` carries the same 3-line literal twice |
| B — `url` variable = single literal | 32 | one-line RHS swap |
| C — inline literal inside the read | 18 | `ols.md` alone has five 150-char `read_stata` literals |
| D — relative / local path | 5 | **portability bugs today** — these break in Colab |
| F — `requests`+`BytesIO` → `np.load` | 4 | resolved by §4.2, not by the package |
| G — live API endpoint | 4 | carve-out |
| H — `scipy.io.loadmat` | 1 | `dataBHS.mat`, see §8.4 |

### 5.2 The honest case for the package

Classified in the worklist: **13 sites are structural** — `qeld` deletes real logic — of which **6 are
convertible today** and the rest are blocked on the format decision (§8.3, §8.4). **70 are cosmetic**
shortenings of literals adopted in the *recent repoint PRs*; a plain one-line literal would win those back
without a package. 32 are neutral or excluded.

**The case rests on:** those ~10 structural sites, the wasm shim, the host-cutover property, and group D's
portability bugs. **Not** on the read-site tally. Anyone re-reading this plan should weigh it on that basis.

The best diff in the corpus is `lecture-python-advanced.myst/lectures/hansen_jagannathan_1991.md:182`, where
`qeld` deletes a hand-rolled version of itself — a 3-fragment URL literal, a local-vs-remote branch and a
`Path("lectures") / url` fallback, 16 lines to 3, plus an unused `pathlib` import.

### 5.3 `url()` alone covers the corpus

After the `.npy` conversion (§8.3), **`dataBHS.mat` is the only file in the endgame that cannot be read from
a URL**. That is what justifies dropping `fetch()`.

### 5.4 Two latent bugs found, worth fixing regardless

- `inequality.md` imports `pyodide_http` and **never calls `patch_all()`**.
- `short_path.md` calls `requests.get` under Pyodide **with no shim at all**.

Both are incidentally fixed by §3.2's shim, but neither should wait for it.

### 5.5 Two problems no syntax solves

**Generic filenames collide in a flat namespace.** `fred_data.csv`, `fp.dta`, `test_pwt.csv`,
`acs_data_summary.csv` all need renaming at migration — and `mle.md:160` names `mle/fp.dta` **in prose**, so
a rename must be paired with a prose edit found by grep, not by the audit.

**Prose and `{download}` links.** 28 refs; **11 name a data file in two places**. The acute case is
`simple_linear_regression.md` (intro:411/416, zh-cn:421/426), where a `{download}` role and the code read sit
five lines apart containing byte-identical 158-character strings.

---

## 6. Integrity and CI (D9)

**Baseline, stated honestly:** a bare URL read has no integrity guarantee today either. Git at the source is
the guarantee, and it remains the guarantee. This design **declines to add a property rather than removing
one** — important, so nobody later re-adds `fetch()` to recover something the series never had.

| leg | status |
|---|---|
| Committed bytes vs `integrity.sha256`, every manifested file | ✅ **already landed** (#56) — hashes whenever a manifest records a hash, with or without consumers |
| URL *spelling* assertions (`ref == main`, path shape, media host, CORS form) | ✅ **already landed** (#55, #48, #47) — static, from the parsed URL |
| **Live serving-URL fetch vs the manifest hash** | ❌ **the remaining gap** — see below |
| Catalog compile + freshness, shared with `CATALOG.md` | ❌ to build (§3.3) |
| Format tier-1 assertion over the catalog | ❌ to build (§4.2) |

**The live leg belongs post-merge and on a schedule, never on PRs.** `audit-dashboard.yml` gates deploy on
`if: github.event_name != 'pull_request'`, so a PR branch's bytes are never on the host: a new-dataset PR
would 404 and a correction PR would compare old served bytes against a new manifest hash. Both fail by
construction — and those are exactly the PR classes such a gate would exist for.

This leg catches what the committed-bytes check structurally cannot: an LFS pointer served instead of
content, a Pages misconfiguration, a stale CDN, a 404. It opens an issue on failure rather than blocking.

**Recorded gap:** a reader running a downloaded notebook years later against a drifted host gets no warning
in their own session. That is **also true today**; the scheduled leg catches drift centrally, so protection
is indirect. Net position after this work: strictly better than today, short of a hashing client.

---

## 7. Development plan

Ordering is forced by one constraint: **the audit must learn the call form before any consumer adopts it**,
or every migrated read classifies `local-path` and the dashboard inverts.

| phase | work | gate |
|---|---|---|
| **Q1 — Audit first** | `build_audit.py` learns `qeld.url('X')` → pattern `qeld`, counted migrated **and terminal**. For `pattern == 'qeld'`, assert the key exists in `lectures/` and is not deprecated — otherwise the qeld path loses every assertion #55/#48/#47 added. `migration.yml`: `final` := canonical-host *or* qeld | `audit.json` `stats` and `problems` unchanged on today's repos (**not** "byte-identical" — the audit stamps `date.today()`) |
| **Q2 — Schema hygiene** | Document `read_as` (used in 6 manifests) and `sheets` (8) in `manifest-schema.yml` — both are in use and neither appears in the file `AGENTS.md` calls "the authoritative, commented field reference". Add `deprecated:` (new, used nowhere yet) since §3.3 warns on it. `shape` is already documented. Delete `then: "iloc[1:]"` from `longprices.xls.yml:70` by moving `iloc[1:]` into the lecture — a post-read transform encoded as a string to evaluate is exactly what D5 excludes | `manifest-schema.yml` covers every field any manifest uses. Needs none of #14's decisions — do not block on it |
| **Q3 — Package** | `packages/qeld/`: `url()`, `info()`, context detection, advisory catalog. Catalog compiler shares a freshness gate with `CATALOG.md`. Format tier-1 assertion. First release to PyPI via trusted publishing | Offline suite green on every PR: catalog compiles and is fresh; unknown key warns and still returns a URL; URL form correct per detected context; suffix fidelity incl. `.csv.gz`; `info()` fields present. CPython matrix |
| **Q4 — Live leg** | Post-merge + scheduled job: fetch each served URL, compare to the manifest hash, open an issue on failure | Green on `main`; an induced failure opens an issue |
| **Q5 — Browser session** | `%pip install qeld==<v>` in a real `lecture-wasm` page (**`%pip` routes through piplite, not micropip** — a console `micropip.install` is a false pass); `pd.read_excel(qeld.url('mpd2020.xlsx'), sheet_name='Regional data', header=[0,1,2], index_col=0)`; a `.csv.gz` read; record observed Pyodide and pyodide-kernel versions | Written pass/fail. Fail ⇒ wasm keeps URLs and the plan proceeds for the CPython repos |
| **Q6 — Pilots, by win** | `hansen_jagannathan_1991` (deletes the dual-path loader — the best diff); `french_rev` (the `base_url` block, intro **and** wasm together per repoint rule 2); `subjective_beliefs_business_cycles` or `match_transport` (group D, a real portability bug) | Diff is the URL expression only; intro figure-hash equality; wasm = re-run Q5's checklist on the pilot page with the console transcript filed. On pass: tag 1.0, freeze the API |
| **Q7 — Sweep by win** | The remaining structural sites, then cosmetic sites at leisure or never. `AGENTS.md` gains §4.1 verbatim, §4.2, and the note that repoint rules 5–6 do not apply to qeld call sites | `migrated` meter reflects qeld refs; no lecture regresses |

**Effort note:** Q3 is not a weekend. The package is small, but the catalog compiler, the tier-1 assertion,
the offline suite and PyPI trusted-publisher configuration are four separate pieces, and the last is not a
code task.

**Pyodide version pinning is accidental** — the version ships inside `thebe-lite.min.js` inside the theme
zip, so a CSS-only theme bump moves the Python runtime. Record Q5's verdict as "Pyodide 0.27 as shipped by
thebe-lite in quantecon-theme v2.1.0" and re-run when the theme moves.

---

## 8. Ambiguities — decide before the phase that needs them

### 8.1 `pandas_panel`'s carve-out — permanent or revisited?

The prose advertises the URL as something a beginner can paste into a browser. Converting is a pedagogical
loss with no offsetting gain (those files already resolve to data-lectures in the form `qeld` emits). The
alternative is rewriting the prose, which is a larger edit than the one being justified. **Needed by Q7.**

### 8.2 The markdown-time story for `{download}` links

`qeld.url()` cannot appear in markdown. Options: convert both and accept two spellings; leave those lectures
alone; or give `qeld` a markdown-time story (a MyST substitution, or point prose at `CATALOG.md`). Until
answered, "convert neither" is the default. **Needed by Q7.**

### 8.3 The `.npy` pair — now a breaking change

`caron.npy` and `nom_balances.npy` are (63, 2) and (81, 2) float64 arrays whose manifests already name the
columns (`date`/`specie_value`, `date`/`nominal_balances`). Converting to CSV deletes `requests`, `BytesIO`
and two imports from `french_rev` in every consuming repo.

**But the window closed.** When this was analysed both files had `consumers: []`; the A3 set has since been
repointed (#49) and both now have two consumers. So this is no longer a free replacement — it needs the
`AGENTS.md` "new vintage → new filename" treatment (`caron.csv` lands alongside, consumers opt in, the `.npy`
is swept later) or a coordinated set under repoint rules 1–3. **Decide before Q6**, since `french_rev` is a
pilot.

### 8.4 `dataBHS.mat` — convert at migration, or exclude?

5,588 bytes; `c`, `rb`, `rs`, each (236, 1) float64; the lecture uses only `data['c']` and the read is inside
a `hide-input` cell, so nothing about it is taught. Trivially a 236×3 CSV — but see §4.3 on the read. A Track
C decision; the only true impossibility among static files.

### 8.5 Is `lecture-intro.zh-cn` in scope?

It carries data reads, appears in **zero** `consumers` blocks, is excluded from `SCAN_REPOS` by decision, has
no data CI, publishes on a `publish*` tag, and inherits install cells automatically via the `.md`-only sync —
so it acquires whatever intro acquires without anyone deciding. It also has files with no data-lectures key
and no business having one (`country_code_cn.csv`, a translation asset).
**Recommendation: explicit non-goal for v1, with one fixed rule instead of machinery — any sweep touching an
intro file also touches zh-cn.**

### 8.6 The rename list for generic filenames

§5.5. Needs a pass before Tracks B and C migrate, and each rename needs its prose pairing found by grep.

### 8.7 Open from the original report

- Ask Spencer/Tom what actually retired `qeds` — it is dead as a project but **still installable** (PyPI
  returns 200 for 0.7.0, not yanked), one letter-transposition from `qeld`. Consider reserving
  `quantecon-data` and `qedata` as stubs.
- `data.quantecon.org` DNS (#37) is the nearest unblocked item and races this work for the same weekend.
- Publishing `qeld` does **not** move #35's licensing gate — it rehosts nothing and fetches the same public
  URLs `pandas_panel` reads today. Do not add a release check that fails on `redistribution: restricted`;
  `countries.csv` is restricted and unresolved, so it would block every release from day one.

---

## 9. Corrections to the original design report

Recorded so they are not re-proposed. The report is superseded by this document.

| claim | status |
|---|---|
| "18/18 manifests", "all 18, not a sample" | stale before the ink dried — 24 manifests, 27 files on `main` |
| Exact CalVer pins, "the install cell names the data vintage" | a version cannot pin bytes — §2.1 |
| "CI fails with `IntegrityError`; that failure *is* the rebuild signal" | wasm CI does not execute; intro is `execute_notebooks: "cache"` and a data correction changes no code, so PRs are cache hits |
| "no lecture-content edits, ever" | the install cell is lecture content, and prose data URLs already exist |
| "six different URL ways" | the audit says five in use |
| "closes #8" | #8's catalog box was already ticked; this adds the freshness CI |
| A `~200-line prototype` and an evidence document | neither exists on disk; `git log --all` has zero hits for `qeld`. Both load-bearing prototype claims re-derive from the manifests |
