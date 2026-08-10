# qeld migration catalog — how the lectures consume data today, and what each idiom becomes

**Date:** 2026-08-10 · **Status:** design input, superseded on decisions by `PLAN-QELD-PACKAGE.md`.
**Purpose:** the worked evidence behind the call-site rule — what each conversion actually looks like.
**Method:** every static data read in six lecture repos (40 lectures, 115 read sites) enumerated from source,
clustered by idiom, with verbatim current code.

> **Snapshot, not a live view.** Both this repo and `lecture-python-intro` moved after this was produced —
> notably the A3 `french_rev` set was repointed in #64's predecessor #49, which changes §3 F's status from a
> free conversion to a breaking one (`PLAN-QELD-PACKAGE.md` §8.3). Re-verify any example before acting on it.

---

## 1. The unit of work is not 115 reads

115 read *sites*, but **23 of them are downstream uses of a variable assigned earlier** —
`pd.read_excel(data_url, …)` where `data_url` was set once. `french_rev` reads `dette_url` six times;
`long_run_growth` reads `data_url` three times.

So the real unit is **~78 URL definitions**. One `qeld.url()` call serves N reads. This is the single most
important fact for choosing syntax: a form that preserves the variable converts one line and leaves N reads
untouched; a form that inlines has to touch all N.

| idiom | definitions | current verdicts |
|---|---:|---|
| **A** — split string literal across lines | 23 | all simpler |
| **B** — `url` variable = single literal | 32 | 15 simpler, 11 same, **all 6 more_complex** |
| **C** — inline literal URL inside the read | 18 | all simpler |
| **D** — relative / local path | 5 | 2 impossible |
| **F** — `requests`+`BytesIO` → `np.load` | 4 | all same |
| **G** — live parameterised API endpoint | 4 | all impossible |
| **H** — `scipy.io.loadmat` | 1 | impossible |
| *(downstream reads of an existing variable)* | *23* | *unchanged by construction* |

---

## 2. The three candidate syntaxes

- **S1 — inline:** `pd.read_csv(qeld.url('x.csv'))`
- **S2 — two-step always:** `url = qeld.url('x.csv')` then `pd.read_csv(url)`
- **S3 — mirror the existing shape:** replace only the URL expression; inline stays inline, a variable stays
  a variable.

---

## 3. The catalog — verbatim, by idiom

### A. Split string literal (23) — the pattern the design was built for

Two sub-shapes. **A1, assigned to a variable** (`polars.md:160-163`):

```python
# CURRENT
url = ('https://raw.githubusercontent.com/QuantEcon/'
       'lecture-python-programming/main/lectures/_static/'
       'lecture_specific/pandas/data/test_pwt.csv')
df = pl.read_csv(url)

# S2 / S3 (identical here)
url = qeld.url('test_pwt.csv')
df = pl.read_csv(url)
```

**A2, split inline inside the read** (`risk_aversion_or_mistaken_beliefs.md:1613`):

```python
# CURRENT — 5 lines
data = pd.read_csv(
    'https://raw.githubusercontent.com/QuantEcon/lecture-python-advanced.myst/refs/heads/'
    'main/lectures/_static/lecture_specific/risk_aversion_or_mistaken_beliefs/fred_data.csv',
    parse_dates=['DATE'], index_col='DATE'
)

# S1 / S3 — 1 line
data = pd.read_csv(qeld.url('fred_data.csv'), parse_dates=['DATE'], index_col='DATE')
```

**Verdict:** the clearest win in the corpus. `polars.md` carries the *same* three-line literal twice
(`:160` and `:346`), which a student has to re-read to confirm it is the same file.

### B. `url` variable = single literal (32) — where every failure lives

```python
# CURRENT (pandas_panel.md:68 / :78)
url1 = 'https://github.com/QuantEcon/data-lectures/raw/main/lectures/realwage.csv'
realwage = pd.read_csv(url1)

# S1 — destroys the variable; every downstream read must change too
realwage = pd.read_csv(qeld.url('realwage.csv'))

# S2 / S3 — one-line RHS swap, downstream reads untouched
url1 = qeld.url('realwage.csv')
realwage = pd.read_csv(url1)
```

**Verdict:** the six `more_complex` gradings in this group were scored against **S1**, which needlessly
destroys a variable the lecture reuses. Under S2/S3 the complaint largely evaporates — the diff is one
line's right-hand side.

**What survives the fix:** `pandas_panel`'s three reads still lose something real. The prose immediately
above reads *"The dataset can be accessed with the following link:"* followed by a cell containing nothing
but the URL, so a beginner can paste it into a browser. All three files already point at data-lectures in
the exact form qeld emits off-Pyodide, so there is no host-migration gain to offset it. This is a
**pedagogical** objection, not a syntactic one, and no syntax fixes it. *(Note: `pandas_panel` exists in both
`lecture-python.myst` and `lecture-python-programming` — the two sweeps graded the same content differently,
which is why the `more_complex` count is 4–8 rather than exactly 6.)*

### C. Inline literal URL inside the read (18) — where S2 loses

```python
# CURRENT (ols.md:94) — a 150-char literal that overflows every page width
df1 = pd.read_stata('https://github.com/QuantEcon/lecture-python.myst/raw/refs/heads/main/lectures/_static/lecture_specific/ols/maketable1.dta')

# S1 / S3 — 1 line
df1 = pd.read_stata(qeld.url('maketable1.dta'))

# S2 — 1 line becomes 2, for nothing
url = qeld.url('maketable1.dta')
df1 = pd.read_stata(url)
```

**Verdict:** `ols.md` alone carries five of these. The prose above each already names the file
(`maketable2.dta`), so the qeld key matches the words on the page better than the URL does. **S2 is worse
than the status quo here** — this is the group that rules out "always two-step".

### D. Relative / local path (5)

```python
# CURRENT (subjective_beliefs_business_cycles.md:149)
data_path = '_static/lecture_specific/subjective_beliefs_business_cycles/'
macro_q = pd.read_csv(data_path + 'bbh_macro_quarterly.csv', index_col='YYYYQ')

# any syntax
macro_q = pd.read_csv(qeld.url('bbh_macro_quarterly.csv'), index_col='YYYYQ')
```

**Verdict:** these relative paths are **portability bugs today** — they break in Colab and in downloaded
notebooks. Two of the five are `country_code_cn.csv`, a zh-cn translation asset with no data-lectures key
and no business having one.

### F. `requests` + `BytesIO` → `np.load` (4) — resolved by the format decision, not by syntax

```python
# CURRENT (french_rev.md:725-728) — plus `import requests` and `from io import BytesIO` at :73-74
caron_response = requests.get(base_url + 'caron.npy')
nom_balances_response = requests.get(base_url + 'nom_balances.npy')
caron = np.load(BytesIO(caron_response.content))
nom_balances = np.load(BytesIO(nom_balances_response.content))

# AFTER the .npy → .csv conversion (review §6.3)
caron = pd.read_csv(qeld.url('caron.csv')).to_numpy()
nom_balances = pd.read_csv(qeld.url('nom_balances.csv')).to_numpy()
```

**Verdict:** graded "same" by the sweep only because it did not know about the CSV conversion. Converted,
four lines and two imports go, and the intro copy's `np.load('datasets/caron.npy')` local path goes with
them. This is the second-best diff in the corpus and it is bought by a **data** change, not a package
feature.

### G. Live parameterised API endpoints (4) — out of scope, and say so loudly

FRED graph queries with ~700-character query strings encoding series id, date range and chart options:
`phillips_drifts_volatilities.md:2213`, `pandas.md:514`, `pandas.md:532/552`, `polars.md:557-572`.

`qeld.url()` keys bare filenames and cannot express `?id=CPIAUCSL%2CUNRATE%2CTB3MS`. **The trap:** three of
these end in `.csv` and carry the ugliest literals in the corpus (`polars.md`'s is 16 continuation lines), so
they are the most tempting to convert by mistake. In `pandas.md` the raw URL is the explicit *subject* of a
teaching section on `requests` and error handling — hiding it would be a pedagogical regression on top of an
impossibility.

### H. `scipy.io.loadmat` (1)

```python
# CURRENT (five_preferences.md:1848)
data = loadmat('dataBHS.mat')

# with qeld and no format change — nobody would ship this
data = loadmat(io.BytesIO(urllib.request.urlopen(qeld.url('dataBHS.mat')).read()))
```

**Verdict:** the only true impossibility among static files. Resolved by the format convention (convert to
CSV) or by exclusion — never by syntax.

---

## 4. Syntax verdict

| idiom | n | S1 inline | S2 two-step always | S3 mirror shape |
|---|---:|---|---|---|
| A1 split → variable | ~15 | ✗ kills the variable | ✅ | ✅ |
| A2 split inline | ~8 | ✅ | ✗ adds a line | ✅ |
| B variable = literal | 32 | ✗ kills the variable, touches N downstream reads | ✅ | ✅ |
| C inline literal | 18 | ✅ | ✗ 1 line → 2 | ✅ |
| D local path | 5 | ✅ | ✅ | ✅ |

**S3 is the only candidate that wins on every idiom**, and it has a property the others lack:

> Under S3 the diff is *always and only* the URL expression. A reviewer can verify a migration PR by reading
> the changed lines alone — there is no restructuring to audit.

That matters for a ~78-site sweep, and it satisfies the maintainer's bar by **construction** rather than by
argument: the lecture's shape is unchanged, so it cannot have become harder to read.

**The rule, for AGENTS.md:**

> Lecture code reads published data through `qeld.url('<filename>')`, substituted **in place of the URL
> expression the lecture already uses** — an inline literal becomes an inline call, an assigned variable
> keeps its assignment. The reader (`pd.read_*`, `pl.read_*`, …) and all its kwargs stay visible and
> unchanged.

Carve-outs: live-API reads (group G); reads whose literal URL is itself the lesson (`pandas_panel`); and
reads whose file is also named by a prose or `{download}` link, until that has an answer (§5).

---

## 5. Two problems no syntax solves

### 5.1 Generic filenames collide in a flat namespace

The published tree is flat, so the key is a bare filename. Several pending files are far too generic to
survive it:

| file | repo of origin | problem |
|---|---|---|
| `fred_data.csv` | advanced | names a source, not a dataset |
| `fp.dta` | python.myst | two letters |
| `test_pwt.csv` | programming | "test" |
| `data.csv` | programming (`about_py.md`) | referenced but never exists |
| `acs_data_summary.csv` | advanced | plausible but claims a whole survey |

These need renaming at migration. **And a rename breaks text qeld cannot reach**: `mle.md:160` names
`mle/fp.dta` in prose. So the rename must be paired with a prose edit, in the same PR, found by grep rather
than by the audit.

### 5.2 Prose and `{download}` links

28 prose/`{download}` refs; **11 name a data file in two places**. The acute case is
`simple_linear_regression.md` (intro:411/416, zh-cn:421/426), where a `{download}` role and the code read sit
**five lines apart containing byte-identical 158-character strings**. Convert the code and the page shows a
raw URL in prose and an opaque call in the cell, with no way for a student to see they agree — and they can
drift silently.

Options: convert both and accept two spellings; leave those lectures alone; or give qeld a markdown-time
story (a MyST substitution, or point the prose at `CATALOG.md` instead of the file). Currently unanswered,
and it is the strongest argument for the "convert both or neither" carve-out.

---

## 6. What this implies for the package

1. **`url()` returning a string is confirmed as the right primitive** — S3 only works because the return
   value can sit anywhere a URL literal sits today.
2. **No second function is needed for the static corpus.** Groups F and H are resolved by the *format*
   convention; group G is out of scope. `open()`/`fetch()` would exist only to serve files the format rule
   says should not exist.
3. **The win is concentrated, not broad.** Of ~78 definitions, roughly 10 see qeld delete real logic; ~50 are
   cosmetic shortenings of literals adopted in recent repoint PRs; the rest are neutral. The case for the
   package rests on those ~10, the wasm shim, the host-cutover property, and the portability bugs in group D
   — **not** on the read-site tally.
4. **Rollout should be ordered by win, not by migration track.** Structural sites first
   (`hansen_jagannathan_1991`'s dual-path loader, `french_rev`'s `base_url` block, `ols.md`'s five literals,
   `polars.md`'s duplicated literal, group D's portability bugs). Cosmetic-only sites can wait indefinitely.
5. **Two latent bugs qeld incidentally fixes**, worth their own issue regardless: `inequality.md` imports
   `pyodide_http` and never calls `patch_all()`; `short_path.md` calls `requests.get` under Pyodide with no
   shim at all.

---

## 7. Open

- The `pandas_panel` pedagogical carve-out — permanent, or revisited if the prose is rewritten?
- The markdown-time story for `{download}` links (§5.2).
- The rename list and its prose pairings (§5.1) — needs a pass before Tracks B and C migrate.
- `dataBHS.mat`: convert at migration, or exclude.
