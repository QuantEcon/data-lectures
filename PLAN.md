# PLAN — `data-lectures` (formerly `QuantEcon/data`)

**Status:** active roadmap (last updated 2026-09-01) — **the repo is LIVE**: the first repoint merged 2026-07-17 (P1, `lingcod_msy_recovery.csv` → `msy_fishery`), so published filenames are an API from here on

**Where the numbers stand (`audit.json`, 2026-08-31):** **40 of 40 static datasets migrated and repointed — the static migration completed 2026-08-18** ([#98](https://github.com/QuantEcon/data-lectures/pull/98), [#99](https://github.com/QuantEcon/data-lectures/pull/99)); 23 lectures still fetch live API data (Track E); 24 committed orphans (Track X); 0 legacy-repo references; 2 URL forms in use.

**`CATALOG.md` and `migrated` both say 40 today, and that agreement holds only while no wave is in flight.** They count different things: `migrated` counts datasets whose *consumers* read this repo; the catalog counts datasets that *live* here. They agree only when no wave is in flight. The P3 fold is the worked example — the six `high_dim_data` files landed 2026-08-10 at `status: landed` with `consumers: []`, opening a six-file gap that closed on 2026-08-11 when PR set C repointed them and [#69](https://github.com/QuantEcon/data-lectures/pull/69) flipped the records. Expect that gap again for the duration of any wave that lands ahead of its repoints, which is the convention here.

Every figure on that line comes from `stats` in the generated `audit.json`, and every figure below that restates one is a copy that can drift — as all seven of them had by 2026-08-07, each understating progress by three repoint sets. Re-read them from `audit.json` before quoting them, and prefer citing the generated file over this document.

This repository is being shaped into the **single canonical repository for data consumed by the QuantEcon lecture series**, referenced by stable URLs and documented in the manual.

## Governing threads

| Thread | Role |
| --- | --- |
| [QuantEcon/meta#336](https://github.com/QuantEcon/meta/issues/336) | Design discussion / future QEP — the convention itself |
| [QuantEcon/data#8](https://github.com/QuantEcon/data/issues/8) | Scaffolding checklist for **this repo** (this PLAN executes it) |
| [QuantEcon/meta#337](https://github.com/QuantEcon/meta/issues/337) | Live hosting risks + `high_dim_data` shape-up + orphan sweep in lecture repos |
| [QuantEcon/meta#338](https://github.com/QuantEcon/meta/issues/338) | Pilot: migrate one dataset per hosting pattern, landing here |
| [QuantEcon/QuantEcon.manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108) | Draft `styleguide/datasets.md` — the convention's design surface |
| [QuantEcon/data#1](https://github.com/QuantEcon/data/issues/1), [#2](https://github.com/QuantEcon/data/issues/2), [#4](https://github.com/QuantEcon/data/issues/4) | Pre-existing execution items (LFS, fold in `high_dim_data`, repoint lectures) |
| [QuantEcon/workspace-lectures#14](https://github.com/QuantEcon/workspace-lectures/issues/14) | Standing cross-repo tracker for the migration — tracks A–E and X–Y, repoint rules, outstanding write-backs (it began as the pilot's session work plan) |

## Where we are

**Update 2026-07-16 — the layout below has been flattened (Phase 2).** The 8 in-use static files and `business_cycle_data.csv` now sit directly in `lectures/`; `scripts/` moved to the root; the 3 no-consumer files were dropped (see Phase 6). The audit that follows is retained as the record of what was migrated and what state each file was in — it is the input to Phases 6 and 7, and the `consumers` column of the manifests still has to be backfilled from it.

### The audit (2026-07-15)

- 12 data files for `lecture-python-intro` under a **consumer-keyed layout** (`lecture-python-intro/{static,dynamic,scripts}/`), in three distinct states:
  - **8 duplicates of data in active use** — `mpd2020.xlsx`, `longprices.xls`, `chapter_3.xlsx`, `assignat.xlsx`, `dette.xlsx`, `fig_3.xlsx`, `caron.npy`, `nom_balances.npy` are consumed by intro lectures (`long_run_growth`, `inflation_history`, `french_rev`), but via intro's **own copies** (own-repo URLs, or local paths for the `.npy` pair) — these are the Phase 8 repoint targets
  - **2 dead on both ends** — the World Bank GDP-per-capita CSV and its metadata twin are orphaned in intro too; nothing reads either copy anywhere
  - **2 never adopted** — `business_cycle_data.csv` (the one dynamic snapshot; intro's `business_cycle` still fetches live from wbgapi/FRED) and `fig_3.ods` (a source-format twin of `fig_3.xlsx`, referenced by nothing)
- one manual refresh script (`builders/business_cycle.py`), run by hand — it has fetch/transform/write but **no validate stage**
- **no `.github/`** — no CI, no PR validation, no scheduled refresh
- no LFS, no per-dataset manifests, no license records
- referenced by **zero lectures** (confirmed by the audit and by live GitHub code search, 2026-07-16) — the Feb 2025 migration (data#5–#7) landed the files but the repoint (data#4) never happened. Until the first repoint merges, everything here can be restructured freely

## Where we're going (per the draft convention)

- **Flat published tree** at `lectures/`, served over the raw GitHub forms (and GitHub Pages), CORS-open for pyodide/JupyterLite. **The custom-domain plan (`data.quantecon.org`) was retired 2026-08-12**: the stable consumer interface is the `qeld` package (`PLAN-QELD-PACKAGE.md`, D11), not a branded host — lectures read `qeld.url('<filename>')` and the direct URL forms below are standing, not interim
- Every dataset classified **verbatim / constructed / dynamic snapshot**, each with a manifest — authoritative field reference in `manifest-schema.yml`, as revised by the P1 pilot (`integrity`, `builder_status`, `known_nulls` and `license.verified` joined the original sketch of `source` / `license` / `retrieved` / `schema` / `consumers` / `maintainer` / `cadence`)
- Constructed and dynamic datasets ship their **builder**; dynamic datasets get **scheduled refresh-as-PR** plus a weekly **sources-alive canary**
- The published tree is **100% plain git**; per-path LFS is confined to `sources/`, which is never served. Storage does **not** decouple from hosting — the URL a consumer must write is a function of how the file is stored, and there is no browser-safe form invariant under a storage flip (repoint rule 6, and [#58](https://github.com/QuantEcon/data-lectures/issues/58) for the ladder above 100 MiB)

## Repoint rules

Six rules learned the hard way, three of them the hard way twice. Rules 1-3 are about *ordering* and none is enforced by CI — the strict audit catches rule 2 only after the fact, and cannot see rule 3 at all. Rule 4 is about *scope*. Rules 5 and 6 are about *URL form and host*, and are the ones CI does cover: since [#55](https://github.com/QuantEcon/data-lectures/pull/55) the strict audit fails on the `github.com/*/raw/` form in `lecture-wasm` (rule 5), on any `data-lectures` reference served from the media host (rule 6), and on a reference whose ref is not `main`, whose path is not `lectures/<file>`, or whose file is not committed here. It still cannot see `lecture-intro.zh-cn` or `lectures/_static/**`.

### 1. Repoint a sibling reader before deleting the file it reads

`lecture-wasm` mirrors `lecture-python-intro`'s sources and fetches intro's **committed blobs** by URL — e.g. `long_run_growth.md` reads `raw.githubusercontent.com/QuantEcon/lecture-python-intro/main/lectures/datasets/mpd2020.xlsx`. Deleting intro's copy in the repoint PR therefore 404s the wasm build immediately.

So the general rule "delete the lecture repo's own copy in the same repoint PR" holds **only** when no sibling reads that copy. Where one does, the sibling's repoint must land **first or together**, and the deletion goes in the same set — never in an earlier PR with the sibling's fix scheduled later.

This affects every `intro` + `wasm` dataset, which is both of the multi-consumer files remaining below.

**The consumer set is the org, not `manifest.yml` and not `SCAN_REPOS`.** A repo that fetches another repo's committed blobs by URL is a rule-1 consumer regardless of how its content is produced, so the sweep before a deletion must enumerate the organisation. Three classes sit outside this repo's eight scanned repos and have each already been missed once:

| Class | Repos | Why it is missed |
| --- | --- | --- |
| **Translations** | five of the six live editions read another repo's blobs — everything except `lecture-python-programming.ml` | excluded from `SCAN_REPOS` by decision (`scripts/build_audit.py:46-47`), so no audit run can ever see them. `lecture-intro.zh-cn` alone held 7 reads of the `high_dim_data` six, repointed by hand in QuantEcon/lecture-intro.zh-cn#292 |
| **Generated mirrors** | `lecture-python-intro.notebooks` | auto-published, so it self-heals on the next publish — but only *after* one |
| **Course forks and canaries** | `tom-econ370-2025`, `test-actions-lecture-intro` | not in any manifest, publish their own Pages sites, and no CI in the family covers them |

Sweep by cloning and grepping, not with `gh search code` on a URL — code search does not index bare URLs and returns a confident zero. It **does** index repo-name tokens and quoted path fragments, so `gh search code 'high_dim_data org:QuantEcon'` finds every consumer of that repo including the translations; use that form where a distinctive token exists, and a Trees-API sweep over `gh repo list QuantEcon --limit 400` otherwise (~2 minutes for 277 repos).

### 2. Repoint every consumer of a dataset together

The strict audit has **no green state for a partially-repointed dataset**. `scripts/build_audit.py` fails a record marked `pending`/`landed` while any consumer already reads data-lectures, *and* fails one marked `repointed`/`final` while any consumer still does not. That is deliberate — it is what makes the tracker trustworthy — but it means a dataset with two consuming repos cannot be moved one repo at a time without the drift alarm firing in the gap.

**2 of the 17 remaining datasets have two consuming repos, and both are `lecture-python-intro` + `lecture-wasm`** — `life-expectancy-vs-gdp-per-capita.csv` and `usa-gini-nwealth-tincome-lincome.csv`. (Six of the eight this line used to name were the `high_dim_data` files, repointed 2026-08-11.) There is no other cross-series coupling left; the last one was the P2 `pandas_panel` trio, already done. (`graph.txt` is **not** in this count and is no longer a Track A item at all — `lecture-wasm` used to read intro's committed copy, which is what made it look like a one-consumer dataset; that read is gone and it is now embedded in every consuming lecture. See the Track A row below.)

**"Two consuming repos" is the audit's count, not the consumer set.** `SCAN_REPOS` is the eight Python-family repos, so a dataset the dashboard shows with two consumers may have four or five in reality. Measured 2026-08-12, both remaining pairs are read by **five** reference-holders each: intro, `lecture-wasm`, `lecture-intro.zh-cn`, `QuantEcon/test-actions-lecture-intro`, and the generated `lecture-python-intro.notebooks` mirror. The last three are invisible to every audit run — see rule 1.

Practically: one branch name across data-lectures + every consuming repo, PRs opened together, lecture repoints merged first, then the `migration.yml` flip to `repointed` — that last push is what re-runs the audit, and by then reality and the tracker agree.

This constrains the **lecture PRs**, not only the tracker flip. Merging one half of a set while the other sits open partially repoints the dataset and opens the same window — observed on 2026-08-06, when `lecture-wasm#53` merged ahead of `lecture-python-intro#824` and left `main` failing on both files until the second landed.

### 3. Repoint, publish, *then* delete — the published site lags `main`

Rules 1 and 2 protect the **repositories**. Neither protects the **published site**, and that gap is where the first real breakage happened.

`lecture-python-intro` publishes on a **`publish*` tag**, not on push to `main`. So merging a repoint does not refresh the live site: the already-published notebooks keep the *old* URL, and if the same PR deleted the file, that URL now 404s. Set 1 proved it — after [lecture-python-intro#823](https://github.com/QuantEcon/lecture-python-intro/pull/823) merged, the notebook served at `intro.quantecon.org` still carried `…/lecture-python-intro/raw/main/lectures/datasets/mpd2020.xlsx`, which had just been deleted. The window stayed open until a publish was tagged.

**The rendered HTML is fine** — figures are baked at build time, so a reader browsing the site sees nothing wrong. The breakage is confined to the downloadable notebook, the Colab link, and `{download}` targets: i.e. every reader who actually *runs* the lecture.

So a repoint set is **two phases**:

1. **Repoint the URLs, keep the files.** Merge, then publish. Now the published notebooks fetch from data-lectures while the old paths still resolve — neither the old site nor the new one can break.
2. **Delete the old copies.** Nothing references them in the repo *or* on the live site.

Cost is one extra PR per set and a slower orphan cleanup; the benefit is that no reader-facing window exists at any point.

**Per-repo publish triggers matter**, so check before assuming:

| Repo | Trigger | Needs two phases? |
| --- | --- | --- |
| `lecture-python-intro` | `publish*` tag (manual) | **yes** |
| `lecture-wasm` | push to `main` | no — self-heals on merge |

A repo that publishes on push needs no split. Neither does deleting a copy that **no lecture reads in either repo** — typically one a repo committed alongside its mirrored sources while the lecture itself fetches the *other* repo's copy by URL (a *mirror-orphan*); `lecture-wasm` held five of these, deleted under Track X (below).

### 4. A migration moves bytes; it does not update them

The copy that lands here is the copy the lectures **already consume**, validated byte-identical in the repoint PR. That is what makes a repoint safe to merge: it provably cannot change a single figure.

Adopting a newer upstream vintage is a *different change* with a different risk profile — it does change lecture output, it needs figures re-reviewed, and it is an author-facing decision rather than an infrastructure one. Conflating the two turns every repoint into a content review and stalls the programme.

So when a migration finds that the committed file differs from what upstream publishes today:

1. **Migrate what the lectures use**, unchanged, with the byte-compare gate as normal.
2. **Record the delta** in the dataset's manifest (`integrity.upstream`) *and* in the register at [#39](https://github.com/QuantEcon/data-lectures/issues/39) — the manifest makes it visible in the catalog from day one, the register is where it gets reasoned about.
3. **Review the register once the migration completes**, and decide each case on its merits.

Two deltas look alike and need opposite responses. *Upstream moved* — a newer vintage exists; adopting it means a **new filename**, per "Corrections vs vintages" in `AGENTS.md`, so consumers opt in. *Our copy diverges* — upstream is unchanged but our file was modified; resolving means reconciling the edit. `mpd2020.xlsx` is the first recorded instance of the second kind, and it is instructive: the local edits are load-bearing for the consuming lecture, so the file and the lecture have to move together.

Detecting these automatically rather than by accident is proposed in [#40](https://github.com/QuantEcon/data-lectures/issues/40).

### 5. In `lecture-wasm`, the URL *form* is part of the contract — use a CORS-clean host

`lecture-wasm` executes its code cells in the reader's browser (JupyterLite/Pyodide via `pyodide_http`), so every pandas URL read is a cross-origin browser fetch, CORS-checked on **every redirect hop**. The `github.com/<org>/<repo>/raw/…` form is a 302 whose response carries an empty `access-control-allow-origin` header — the browser rejects it before the redirect is ever followed. The direct hosts serve `access-control-allow-origin: *` and work.

Learned from the independent validation ([#45](https://github.com/QuantEcon/data-lectures/issues/45) → [#46](https://github.com/QuantEcon/data-lectures/issues/46)): the set 1/2 wasm repoints normalised wasm's URLs to intro's `github.com/…/raw/` form — the one form wasm's runtime cannot fetch. The `raw.githubusercontent.com` URLs they replaced were a deliberate wasm adaptation that looked like an inconsistency. Nothing in CI can catch the break: it exists only inside a browser, and the static pages still return 200 because the wasm build bakes no outputs — figures appear only after in-browser execution, which dies at the first data cell.

| Consumer runtime | Form to use |
| --- | --- |
| CPython — intro site notebooks, Colab, every other series | any resolving form; `github.com/…/raw/` is fine |
| Browser — `lecture-wasm` code-cell reads | `raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/<file>`, and nothing else. **Never the media host** — everything published here is plain git, so it 404s (rule 6) |

`{download}` targets and prose links are plain navigations — CORS does not apply, and the `github.com` form is fine there. The audit classifies references by org/repo across all URL forms, so both spellings count as the same pattern — but the strict build now also checks the *form*: any `lecture-wasm` code-cell read via a `github.com/…` URL fails the audit. That is a **post-merge net, not a gate** — the scan reads each lecture repo's `main`, so a violation turns the dashboard red at the next audit run rather than blocking the offending PR; the repoint PR remains the place the rule is actually upheld. Quick test from any `quantecon.github.io` page console: `fetch('<url>')` — the bad form rejects, the good form resolves.

The requirement outlives the plan that created it: any host `lecture-wasm` reads from must serve `access-control-allow-origin: *` on a direct 200, no redirect hop. The `data.quantecon.org` cutover this criterion was recorded against ([#37](https://github.com/QuantEcon/data-lectures/issues/37)) was retired 2026-08-12 in favor of `qeld` (`PLAN-QELD-PACKAGE.md` D11); the criterion binds again in full if a custom domain is ever revisited.

### 6. `media.githubusercontent.com` is LFS-only — a fold changes the *host*, not just the org

`media.githubusercontent.com/media/<org>/<repo>/<ref>/<path>` is the **LFS media endpoint**. It routes **per path, not per repo** — it resolves only for paths that are LFS-tracked in that repo, and returns **404** for a plain-git file even inside a repo that has LFS enabled (measured on `high_dim_data`'s own un-tracked `README.md` and `cross_section/webscrape_forbes.ipynb`). Measured 2026-08-07:

| URL | Status |
| --- | --- |
| `raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/mpd2020.xlsx` | **200** |
| `media.githubusercontent.com/media/QuantEcon/data-lectures/main/lectures/mpd2020.xlsx` | **404** |

Both hosts send `access-control-allow-origin: *`, so this is **host routing, not CORS** — a distinct failure from rule 5, and it bites CPython consumers too, not only the browser.

**The one piece of work this rule was written for is DONE — everything from here to the end of the rule is the record of it, kept because the mechanism recurs.** `high_dim_data` tracked `*.csv` **and** `*.dta` under a blanket LFS rule, so every consuming lecture read its datasets through the media host. The storage decision landed those six datasets here as **plain git** (both SCF minis fit under the 100 MiB blob limit), which made the media host 404 for them, so **every consuming read had to change host as well as org and repo** — a mechanical org/repo swap preserving the host would have broken all of them. All 28 were repointed on 2026-08-11 and the flip landed as [#69](https://github.com/QuantEcon/data-lectures/pull/69); the acceptance greps at the end of this rule both return nothing today.

The rule itself still binds on any future fold out of an LFS-tracked repo, and the two CI assertions it earned ([#55](https://github.com/QuantEcon/data-lectures/pull/55)) are permanent. Read the tables below as the worked example, not as open work.

**28 source reads are affected across four repos: 22 on the media host, 6 on the `github.com/*/raw/` redirect form.** The `github.com/<org>/<repo>/raw/…` form is a *smart* redirect that routes per path by LFS status, so those 6 survive an org/repo/path swap with no host decision; **the other 22 must change host as well.** Two of the four consumers are invisible to every audit run: `lecture-intro.zh-cn` is excluded from `SCAN_REPOS` by decision (`scripts/build_audit.py:48-57`) — see rule 1 — and `QuantEcon/test-actions-lecture-intro`, the `quantecon/actions` canary, is not a Python-family repo and was never in scope for it.

Counting by repo. Two superseded figures are recorded here because **each has already been mistaken for the total once**: "12 media reads" is the intro + wasm subset, and "21 reads across three repos" omits the canary, which was found late. If a restatement of this rule disagrees with the table below, the table is the one that was measured.

| Repo | media | `github.com/*/raw/` | total | seen by |
| --- | --- | --- | --- | --- |
| `lecture-python-intro` | 5 | 2 | 7 | strict audit (`.md` only) + its own `data-url-guard` |
| `lecture-wasm` | 7 | 0 | 7 | strict audit (`.md` only) + its own `data-url-guard` |
| `lecture-intro.zh-cn` | 5 | 2 | 7 | **nothing** |
| `test-actions-lecture-intro` | 5 | 2 | 7 | **nothing** |
| **all** | **22** | **6** | **28** | |

**The table below is the PRE-FOLD state — the reads as they stood immediately before PR set C, with the host each was on.** It is kept as the record of what was changed, not as a description of any repo today: all 28 now read `raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/<file>`, and the four `data.ipynb:37` rows in particular have said `raw` since 2026-08-11. Line numbers were measured against each repo's `main` on that date and several have already moved. **Re-derive immediately before editing anything** — `lecture-intro.zh-cn`'s drifted by +1 in the course of one afternoon, from a `[translation-sync]` PR that never touched a data-read line, and its `inequality.md` moved by −5 later the same day. Use `bin/zh-fold-lines` in `QuantEcon/workspace-lectures` for zh-cn (no clone needed) and a plain `grep -rn high_dim_data lectures/` for the rest. The bare needle is deliberate here and in the acceptance check below — see the note there.

| Repo | File | Lines | Host **before** the fold |
| --- | --- | --- | --- |
| `lecture-python-intro` | `lectures/heavy_tails.md` | 827, 854, 855, 879 | media |
| `lecture-python-intro` | `lectures/_static/lecture_specific/inequality/data.ipynb` | 37 | media |
| `lecture-python-intro` | `lectures/mle.md` | 93 | `github.com/*/raw/` |
| `lecture-python-intro` | `lectures/inequality.md` | 249 | `github.com/*/raw/` |
| `lecture-wasm` | `lectures/heavy_tails.md` | 827, 854, 855, 879 | media |
| `lecture-wasm` | `lectures/mle.md` | 95 | media |
| `lecture-wasm` | `lectures/inequality.md` | 250 | media |
| `lecture-wasm` | `lectures/_static/lecture_specific/inequality/data.ipynb` | 37 | media |
| `lecture-intro.zh-cn` | `lectures/heavy_tails.md` | 811, 838, 839, 863 | media |
| `lecture-intro.zh-cn` | `lectures/_static/lecture_specific/inequality/data.ipynb` | 37 | media |
| `lecture-intro.zh-cn` | `lectures/mle.md` | 105 | `github.com/*/raw/` |
| `lecture-intro.zh-cn` | `lectures/inequality.md` | 256 | `github.com/*/raw/` |
| `test-actions-lecture-intro` | `lectures/heavy_tails.md` | 822, 849, 850, 874 | media |
| `test-actions-lecture-intro` | `lectures/_static/lecture_specific/inequality/data.ipynb` | 37 | media |
| `test-actions-lecture-intro` | `lectures/mle.md` | 93 | `github.com/*/raw/` |
| `test-actions-lecture-intro` | `lectures/inequality.md` | 249 | `github.com/*/raw/` |

The plain-git decision does not *dissolve* the raw-vs-media trap for the repoint — it **inverts** it. The trap stops being "consumers must know to use the media host" and becomes "consumers already on the media host must be moved off it, in the same PR as the fold."

**Acceptance check for the fold** — scope it to the consuming *lecture trees*. Two of the four paths are not under `repos/`: clone `lecture-intro.zh-cn`, and take the canary from `repos-infrastructure/`, where the workspace already clones it:

    grep -rn 'media.githubusercontent.com/media/QuantEcon/data-lectures' \
      repos/lecture-python-intro/lectures \
      repos/lecture-wasm/lectures \
      repos-infrastructure/test-actions-lecture-intro/lectures \
      <path-to>/lecture-intro.zh-cn/lectures

That must return nothing. The scoping is not cosmetic: the form quoted here before was `… repos/`, which could never pass, because it matched this document's own occurrences of the string — and it also silently omitted the canary, which lives under the *other* clone root. Any restatement of this check must exclude the rules that describe it and include all four consumers.

A second grep is what actually proves the fold, since the one above passes trivially on a tree that was never repointed at all:

    grep -rn 'high_dim_data' <the same four lecture trees>

That must also return nothing.

**The bare needle is deliberate — do not narrow it to `QuantEcon/high_dim_data`.** This is an acceptance gate, and its two error costs are not symmetric: a false positive costs someone five seconds of looking, a false negative ships a broken fold. The broad form also catches a fork reference (`<someone-else>/high_dim_data`) and a URL that lost its org prefix, which the qualified form cannot. And a **non-URL hit inside a lecture tree is a finding, not noise** — org-wide the archive gate is deliberately worded as zero *executable data reads*, because prose mentions there are permanent (frozen reports, `quantecon-book-networks/data/README.md:72`), but inside these four trees a surviving mention of the retired repo is something the close-out should sweep. Measured 2026-08-11: all 28 hits across the four trees are org-qualified URL reads, so the two forms are equivalent today and the broad one only differs on the cases you want to hear about.

This **is** covered by CI now, for the repos the audit scans. A reference classified `pattern: data-lectures` fails the strict audit if it is on `media.githubusercontent.com`, and separately if its `(ref, path)` is anything but `main` + `lectures/<file>`, or if that file is not committed here yet. Those are two independent assertions on purpose: a media URL parses to exactly the same `ref` and `path` as the raw URL beside it, only the host differs, so neither check can stand in for the other. Before this, `scripts/build_audit.py` computed `lfs_media` per reference and asserted on it nowhere — a tree with all 12 `.md` reads left on the media host and `migration.yml` flipped to `repointed` exited `--strict` with code 0, verified end to end.

**The strict audit sees only 12 of the fold's 28 reads** — the `.md` reads in `lecture-python-intro` and `lecture-wasm`. `SCAN_REPOS` is the eight Python-family repos, so `lecture-intro.zh-cn`'s seven reads and the canary's seven are outside it; `lectures/_static/**` is excluded by design, so all four `data.ipynb` copies are too. Those are builder notebooks, which the translation sync never carries either (it is `.md`-only), so they must be changed by hand in every repo and checked by hand.

The `data-url-guard` in `lecture-python-intro` and `lecture-wasm` ([workspace-lectures#23](https://github.com/QuantEcon/workspace-lectures/issues/23) gate 2) recovers two of the sixteen — it greps all of `lectures/`, `_static` notebooks included. **That leaves 14 reads, across `lecture-intro.zh-cn` and `test-actions-lecture-intro`, with no automated check of any kind.** Both are hand-written PRs, verified by hand.

## Migration tracks

The remaining work decomposes by **consuming series** rather than by hosting pattern, because — apart from the `intro`/`wasm` pairing — each series now owns its own data. This is the execution view; the phases below remain the machinery each track passes through.

| Track | Datasets | Coupling | Blocked on |
| --- | --- | --- | --- |
| **A — `intro` + `wasm`** | 17, **all done**. The last two CSVs landed as wave A4 ([#74](https://github.com/QuantEcon/data-lectures/pull/74), flipped in [#75](https://github.com/QuantEcon/data-lectures/pull/75)); `graph.txt` was never a migration — see below | — | — |
| **B — `python.myst`** | 7, **all done**, cut into two waves. **B1′**: the `ols` trio, `fp.dta` and `NEWQDATA.csv` landed in [#79](https://github.com/QuantEcon/data-lectures/pull/79), flipped in [#80](https://github.com/QuantEcon/data-lectures/pull/80). **B2′**: `hansen_singleton_1982/1983_data.csv` landed in [#82](https://github.com/QuantEcon/data-lectures/pull/82), flipped in [#83](https://github.com/QuantEcon/data-lectures/pull/83); both waves independently validated in [#84](https://github.com/QuantEcon/data-lectures/issues/84) | **three consumers, not one** — `lecture-python.zh-cn` reads by URL *and* holds byte-identical copies of all 7 plus both builders (and is outside `SCAN_REPOS`, so the audit cannot see it); `lecture-python.notebooks` lags a publish tag; `lecture-stats` carried a published-site prose link to `fp.dta` behind a daily linkcheck. B2′ adds a fourth kind: the two builders migrate too, and each lecture names them twice outside its data cell | nothing |
| **C — `advanced.myst`** | 6, **all done**. **C1**: the `bbh` pair and `hansen_jagannathan_1991_data.json` landed in [#92](https://github.com/QuantEcon/data-lectures/pull/92), flipped in [#95](https://github.com/QuantEcon/data-lectures/pull/95), validated in [#96](https://github.com/QuantEcon/data-lectures/issues/96). **C2**: `fred_data.csv`, `acs_data_summary.csv` and `dataBHS.mat` (converted to `dataBHS.csv`) landed in [#98](https://github.com/QuantEcon/data-lectures/pull/98), flipped in [#99](https://github.com/QuantEcon/data-lectures/pull/99), validated in [#100](https://github.com/QuantEcon/data-lectures/issues/100) | none by URL — but six other org repos hold byte-identical copies of `acs_data_summary.csv` and `dataBHS.mat`, and `lecture-tools-techniques` publishes its own read of the latter, so acceptance was scoped to advanced's own URLs | — |
| **D — `programming`** | 1, **done**: `test_pwt.csv` rode with wave C2 ([#98](https://github.com/QuantEcon/data-lectures/pull/98), [#99](https://github.com/QuantEcon/data-lectures/pull/99)); its four consuming repos are recorded in [#101](https://github.com/QuantEcon/data-lectures/pull/101) | none | — |
| **E — dynamic / live-API** | the UNRATE twin, then the 15 incidental API lectures | wasm is the forcing customer | [#14](https://github.com/QuantEcon/data-lectures/issues/14) schema decisions, [#26](https://github.com/QuantEcon/data-lectures/issues/26) fetch layer |
| **X — orphan sweep** | **done 2026-09-01** — 23 of the 24 `audit.json` orphans deleted (dp 10, programming 4, intro 4, python.myst 2, wasm 2, `continuous_time_mcs` 1), `python_advanced_features/test_table.csv` kept as an exercise download, plus 46 translation copies the audit cannot see (`lecture-python.zh-cn` 15, `lecture-python-programming.{zh-cn,fr,fa}` 9 each, `.ml` 6, `lecture-intro.zh-cn` 4); twelve PRs, ledger at [QuantEcon/workspace-lectures#57](https://github.com/QuantEcon/workspace-lectures/issues/57) | — | site clearance rides the settle policy, verified at [QuantEcon/workspace-lectures#40](https://github.com/QuantEcon/workspace-lectures/issues/40) |
| **Y — consumer interface (`qeld`)** | the `qeld` package, Q1–Q7 of `PLAN-QELD-PACKAGE.md` — audit support, the package, pilots, then adoption by win; QEP graduation stays | — | nothing — re-scoped 2026-08-12 (D11): the DNS → custom domain → URL-sweep sequence this row used to carry is retired |

**`graph.txt` was closed out as a non-migration (2026-08-12).** It is synthetic teaching data — `provenance: toy`, null in every real provenance field — and the shortest-path exercise teaches its format by quoting the first line, so the data has to stay visible on the page. Hosting it here would have put a toy in a registry that exists to carry provenance. Instead `lecture-wasm` stopped fetching intro's committed copy over the network and embeds it with `%%file` like every sibling ([QuantEcon/lecture-wasm#63](https://github.com/QuantEcon/lecture-wasm/pull/63)), which retired the last cross-repo read of that blob anywhere in the organisation. `graph.txt` consequently no longer appears as a scanned dataset at all. Four repos embed it via `%%file` — intro, dp, jax and wasm — and two of those (intro, dp) also commit a copy the cell overwrites before reading, so those two are shadowed orphans; jax and wasm commit none, which is the cleaner shape. The remaining committed copies (`lecture-intro.zh-cn`, the canary, `lecture-python.zh-cn`, `lecture-dp.monorepo`, `ipynb_pdf_constructor`) are read by nothing. Intro's committed copy is now deletable as Track X — but the same blob sits in **7** repos byte-identically (a further two, `QuantEcon.jl` and `QuantEcon.lectures.code`, hold a 4,692-byte variant differing by one trailing space) and is regenerated at 17 `%%file` sites, including archived `.rst` ancestors that `gh search code` cannot see, so that deletion needed its own per-repo reader sweep rather than an org-wide sweep. **Deleted 2026-09-01** from intro, dp, `lecture-intro.zh-cn` and `lecture-python.zh-cn` (Track X); the one outside-org reader, `devopseng99/project.lecture-wasm`, was recorded and accepted on QuantEcon/workspace-lectures#57. The copies in the canary, `lecture-dp.monorepo`, `ipynb_pdf_constructor`, `QuantEcon.jl` and `QuantEcon.lectures.code` are read by nothing and stay.

`lecture-dp`, `lecture-jax` and `continuous_time_mcs` are **not data consumers** — dp's 10 committed files were inherited orphans and continuous_time_mcs had one orphan scratch file (all deleted 2026-09-01, Track X); jax embeds `graph.txt` via `%%file` and commits nothing.

**Tracks A–D are complete (2026-08-18) and Track X (2026-09-01); E and Y remain.** They were independent of each other and ran in the order A → B → C+D → X. The only hard dependencies left in the programme are: Track E's rollout needs its own template proven first, and Track Y's adoption sweep (qeld Q7) is last.

**Track Y was re-scoped 2026-08-12: invest in `qeld`, defer the custom domain indefinitely** (`PLAN-QELD-PACKAGE.md` D11, where the reasoning is recorded in full). The short form: the package delivers everything the domain would have — a stable interface point that survives backend rework — plus tidier lectures and call-site metadata, without the forever-promise of a branded public host, and so without [#35](https://github.com/QuantEcon/data-lectures/issues/35)'s promotion gate ever coming due. It is a commitment decision, not an effort one: the DNS record remains two actions QuantEcon controls (the stale A record was deleted; the name is NXDOMAIN as of 2026-08-10) and [#37](https://github.com/QuantEcon/data-lectures/issues/37) stays open as deferred-not-dead, reopenable at any time because qeld's base URL stays on the raw forms (never `quantecon.github.io` — D11's redirect trap). The classifier constraint this paragraph used to carry moves with the re-scope: `classify_url` must learn the `qeld.url('X')` pattern **before** any consumer adopts it (qeld Q1), for the same structural reason it would have had to learn the canonical host before a URL sweep — otherwise every migrated read classifies as broken and the dashboard inverts.

### Where this work happens

Repoints span data-lectures plus one or two lecture repos and must land together, which is exactly what [`QuantEcon/workspace-lectures`](https://github.com/QuantEcon/workspace-lectures) exists for: all the repos cloned side by side, `bin/foreach` for cross-repo greps and branch creation, and its stated pattern of *same branch in each repo → edit → commit per repo → one PR per repo*. `data-lectures` is already in its manifest. The artifacts still live here — this PLAN, the manifests, `migration.yml` — and every PR still lands in its own repo; the workspace is the bench, not the destination.

## Phases

Ordering note: phases 1–3 and 6 can proceed now; phase 4's DNS question was resolved 2026-08-12 by deferring it (D11 — see the box below); phase 5 follows layout, **except its go-live guardrails, which must precede the first repoint**; phase 7 needs the sources recorded in phase 6; phase 8 (the pilot) is the first end-to-end pass through phases 2–7's machinery and requires phase 7's byte-compare for the files it touches **plus phase 5's go-live guardrails** — the first repoint turns `raw/main` into a production URL, so the repo must not go live unprotected; phase 9 follows the pilot (interim URL form makes repoints churn-tolerant to start earlier).

### Phase 0 — Scaffolding (this PR)

- [x] `PLAN.md` (this document)
- [x] `AGENTS.md` — conventions and gotchas for agents/contributors working here
- [x] README rewrite: purpose, routing rule, how to add a dataset, links to manual page

### Phase 1 — Identity ✅ (2026-07-16)

- [x] Rename `QuantEcon/data` → `data-lectures` (GitHub redirects preserve all existing URLs, so this was non-breaking)
- [x] Add repo description and topics (`quantecon`, `datasets`, `economics`, `open-data`, `teaching-materials`)

### Phase 2 — Layout (2026-07-16)

- [x] Restructure consumer-keyed tree → flat published tree — `lectures/` is the published root; no folder implies series ownership. Done while zero lectures referenced the repo, so no consumer could break; **that window is now closed**
- [x] Decide where non-published assets live relative to the published tree — `scripts/` and `manifest-schema.yml` sit at the root, outside `lectures/`, and are never served. Manifests are the exception: they live *inside* `lectures/` as sidecars named `<filename>.yml`, so a dataset cannot be moved or removed without its metadata, and CI can assert the pairing with a glob
- [x] Generate an index/catalog page from the manifests — doubles as the dataset registry. `scripts/build_catalog.py` emits `CATALOG.md` (migrated-only registry) from `lectures/*.yml`; regenerate on any manifest change, and a Phase 5 CI check will assert it is current (`git diff --exit-code`). Feeds the Pages index at Phase 4

The sidecar naming uses the **full filename** (`mpd2020.xlsx.yml`, not `mpd2020.yml`) because a stem-keyed sidecar collides when one dataset ships in two formats — exactly the `fig_3.xlsx` / `fig_3.ods` case this repo already had. Strawman until the pilot tests it; see `manifest-schema.yml`.

### Phase 3 — Storage

**Settled 2026-08-06 — the published tree stays 100% plain git.** The two files that drove the LFS requirement do not actually need it: `SCF_plus_mini.csv` is 31.3 MiB and `SCF_plus_mini_no_weights.csv` is 72.4 MiB, both comfortably under GitHub's 100 MiB limit. Keeping `lectures/` free of LFS entirely means **no consumer can ever meet the raw-vs-media URL trap** — it removes the hazard rather than managing it, and the sequencing constraint below stops applying to anything served.

Only one file genuinely forces LFS, and it is not a dataset:

| Path | Contents | Storage | Served? |
| --- | --- | --- | --- |
| `lectures/` | every published dataset, including both SCF minis and the 4 `cross_section` CSVs | **plain git** | yes |
| `sources/` | upstream inputs that builders consume but no lecture reads — `SCF_plus.dta` (99.1 MiB) | **per-path LFS** | **no** |

`sources/` exists as of [#63](https://github.com/QuantEcon/data-lectures/pull/63). Its defining property is **un-refetchability, not size** — all six `committed` builders here fetch from their third-party upstream at run time and none has a committed input, so this is an exception layer rather than a general input tree. Confirmed not served, 2026-08-10: `quantecon.github.io/data-lectures/sources/SCF_plus.dta` and `.../sources/README.md` both return **404**, against **200** for any `lectures/` path.

- [x] Add `sources/` for builder inputs, with `sources/README.md` as the **audit trail**: a **`## <filename>` section per committed file**, recording where it came from, when, its licence, the upstream identifier (DOI where one exists), its `sha256`, and which builder consumes it. That shape is **enforced, not conventional** — `check_sources()` splits the README on `## ` headings and reads the first 64-hex token in each filename-shaped section, so a file documented as a row in a shared table has no recorded hash and fails the required check. (This line previously said "one row per committed file", which was written before the format existed and would now send you into a red build.) A file in `sources/` is not a published dataset and gets no sidecar manifest — this README is its provenance record. Landed in [#63](https://github.com/QuantEcon/data-lectures/pull/63), which also made the README **load-bearing rather than documentary**: `check_consumed_files.py` now asserts that every file here is captured by the LFS rule and hashes to a `sha256` recorded under a `## <filename>` heading, and fails on a README entry naming a file that is not there. It reads the pointer's `oid` rather than the object, so it verifies ~100 MiB under `lfs: false` at zero bandwidth
- [x] Per-path LFS via `.gitattributes`, scoped to `sources/**` only — never a blanket rule like `high_dim_data`'s `*.csv` **and** `*.dta` (data#1). Landed in [#57](https://github.com/QuantEcon/data-lectures/pull/57), with `sources/README.md` excluded so the audit trail stays readable text
- [x] Fold in `high_dim_data` content (data#2; coordinate with meta#337 for consuming-lecture repoints) — the **data** side is done: six datasets plus six manifests and six `migration.yml` records at `landed` in [#62](https://github.com/QuantEcon/data-lectures/pull/62), `sources/SCF_plus.dta` in [#63](https://github.com/QuantEcon/data-lectures/pull/63). The consuming repoints landed 2026-08-11 — see the box below
- [x] ~~**Repoint `generating_mini.md`'s input URL**~~ — **superseded, do not do this.** [#14](https://github.com/QuantEcon/data-lectures/issues/14) settled the question this box was waiting on, and it settled it the other way: the builder lands as **provenance**, `builder_status: committed-frozen`, committed verbatim and not edited at all. The worry behind the box was that archiving `high_dim_data` while `pd.read_stata('https://github.com/QuantEcon/high_dim_data/…')` stands re-introduces a retired-repo dependency. It does not, because the rule requiring a builder to read from `sources/` binds builders that **run** — a never-executed record has no live dependency to re-introduce, and editing it destroys the one property that makes it worth keeping. The substitution is recorded as prose in `sources/README.md`: the input is now committed at `sources/SCF_plus.dta`, byte-identical to what that URL served. The rule still binds fully on any builder that does run
- [x] **Repoint all 28 consuming reads, moving the 22 media-host ones off `media.githubusercontent.com`** — **done 2026-08-11.** They were LFS-tracked in `high_dim_data` and landed here as plain git, so the media host 404s for them and changing only org and repo would have broken every read. The reads span **four** repos, not three: `lecture-python-intro` (7, QuantEcon/lecture-python-intro#832), `lecture-wasm` (7, QuantEcon/lecture-wasm#60), `lecture-intro.zh-cn` (7, QuantEcon/lecture-intro.zh-cn#292) and `QuantEcon/test-actions-lecture-intro` (7, QuantEcon/test-actions-lecture-intro#53) — the last two hand-written and hand-verified, neither visible to any CI. All 28 landed on `raw.githubusercontent.com`, including the 6 redirect-form reads that would have survived a bare org swap: one spelling across four repos, so the "harmonise these two forms" class of fix that broke wasm in [#46](https://github.com/QuantEcon/data-lectures/issues/46) cannot recur. See **repoint rule 6** for the enumeration and the acceptance check, both of which return nothing today. *(The "21 reads / three repos" figure this line once carried is the first three repos only; the canary was found later and has been mistaken for out-of-scope once already.)*
- [x] Set `lfs: false` on **both** workflows that check this repo out, not only the Pages job — landed in [#57](https://github.com/QuantEcon/data-lectures/pull/57). `.github/workflows/audit-dashboard.yml:51` (push to `main` plus weekly, and its paths filter includes `migration.yml` and `lectures/*.yml`, so the fold PR's own files trigger it) and `.github/workflows/consumed-file-check.yml:26` (**every** pull request). `lfs: false` is the *assertion* that nothing published is an LFS object, not a saving: a mis-tracked `lectures/` file then hashes as its pointer and the required check goes red, where `lfs: true` would fetch the real bytes, pass green, and publish a file that resolves only from Pages. On the quota, measured 2026-08-10: the org's net LFS charge for all of 2026 is $0.04 on $1.04 gross, and `high_dim_data`'s bandwidth is 0 GB since June — so the outage scenario is not currently binding. The mechanism is real, though: anonymous public downloads bill the repository owner with no open-source exemption, forks count against the parent, and a **$0 budget blocks LFS downloads** for the rest of the month rather than billing them
- [x] Record in `sources/README.md` that `SCF_plus.dta` is 103,934,093 B — **923,507 B, or 0.88%, under GitHub's hard 104,857,600 B blob limit**. It must stay LFS-tracked permanently; an upstream vintage 1% larger could not be pushed as plain git at all. Landed in [#63](https://github.com/QuantEcon/data-lectures/pull/63), and the margin is why the `git check-attr` precondition is a gate rather than a formality: below the limit a mis-scoped rule does not error, so the push succeeds as plain git and the blob is in history permanently

**Sequencing constraint** (still applies to anything that *does* enter LFS): enabling LFS breaks every `raw.githubusercontent.com` URL for the paths it covers — those URLs return the pointer text with HTTP **200**, so a status-code check is a false green. `pd.read_csv` then raises **nothing at all**: it returns a 2×1 frame whose single column name is `version https://git-lfs.github.com/spec/v1`. (`pd.read_stata` does raise, misleadingly, on the Stata version byte.) Silence is the case that matters, since every affected lecture read is a `read_csv`. Verify with `curl -s <url> | head -1` rather than a status code. Do not LFS-track an existing file until its consumers use a form that survives it; keeping the published tree plain-git means no consumer-facing path is ever affected.

### Phase 4 — Publishing

- [x] GitHub Pages deploy of the published tree, **`lfs: false` at checkout** (inverted by [#57](https://github.com/QuantEcon/data-lectures/pull/57): a mis-tracked file must publish as its pointer, so the mistake is visible rather than masked) — landed 2026-07-17 with the audit dashboard (`.github/workflows/audit-dashboard.yml`, [#20](https://github.com/QuantEcon/data-lectures/issues/20)): the default `quantecon.github.io/data-lectures/` site serves the dashboard at `/` and the published tree at `/lectures/`. The custom domain below stays open
- [x] ~~`data.quantecon.org` DNS + custom domain~~ — **deferred indefinitely 2026-08-12, do not do this without revisiting D11** (`PLAN-QELD-PACKAGE.md` §2.2): the `qeld` package is the stable consumer interface instead of a branded host, and the direct raw URLs are standing rather than interim. The measurement stands for whenever this is revisited: as of 2026-08-10 the name is NXDOMAIN at `quantecon.org`'s own authoritative nameserver, the repo's Pages `cname` is null, and the stale A record and the AWS box it pointed at are gone — so reviving it is two actions QuantEcon controls (create the record, set the custom domain), plus D11's condition that old wheels keep working because qeld's base never sat on `quantecon.github.io`. [#37](https://github.com/QuantEcon/data-lectures/issues/37) stays open as the deferred tracker
- [x] Verify `access-control-allow-origin: *` on served files (pyodide/JupyterLite, meta#143) — **verified 2026-08-06**: `quantecon.github.io/data-lectures/lectures/lingcod_msy_recovery.csv` returns `access-control-allow-origin: *`. The requirement is met on the default Pages domain today and never waited on a custom domain; re-verify only if DNS is ever revisited (D11)
- [ ] Monitor Pages soft limits (~1 GB site, 100 GB/month)

### Phase 5 — Automation (`.github/`)

**Go-live guardrails** — the minimal subset that must precede the first repoint (Phase 8); the rest of this phase follows at its own pace:

- [x] Branch protection on `main`: PRs required (no direct pushes; zero approvals so a solo maintainer can still merge), force-pushes and deletion blocked. Once a lecture repoints, `raw/main` is a production URL and an accidental force-push is a lecture outage (ruleset added 2026-07-17)
- [x] Minimal consumed-file check: CI that asserts every file in `lectures/` whose manifest records an `integrity.sha256` still exists and matches it — rekeyed off `consumers` in [#56](https://github.com/QuantEcon/data-lectures/pull/56), since manifests land ahead of their repoints and the old keying meant the one PR that introduced new bytes was the one PR that never verified them — the narrowest possible test that a PR cannot break a live lecture. Subsumed later by the full PR validation below (added 2026-07-17: `.github/workflows/consumed-file-check.yml`, and made a **required status check** in the `protect-main` ruleset the same day — a red check blocks the merge)

Full automation:

- [x] Audit dashboard workflow ([#20](https://github.com/QuantEcon/data-lectures/issues/20), added 2026-07-17): `.github/workflows/audit-dashboard.yml` rebuilds the full-universe data audit + migration tracker from the 8 lecture repos' `main` (push to main / weekly / dispatch) and deploys it with the published tree to Pages. Strict mode fails the build on an unannotated data reference or a `migration.yml` status the scan contradicts
- [ ] PR validation: manifest schema check + per-dataset invariant tests (expected columns/dtypes, row-count floor, date-range recency, no all-NaN columns, overlap-window agreement with the previous vintage) on every PR touching data. The schema decisions these tests force — column patterns for wide files, `known_nulls` exact-vs-ceiling, a canonical dtype vocabulary — are researched in [#14](https://github.com/QuantEcon/data-lectures/issues/14)
- [x] Retrofit `builders/business_cycle.py` to the four-stage builder contract — **done 2026-09-01**, with the two provenance dumps moved out of the published tree to `provenance/` ([#13](https://github.com/QuantEcon/data-lectures/issues/13)). Its `validate()` is the first to face a *revised* upstream: it bounds the overlap window (5 pp) and prints the revision summary rather than asserting equality, which is the review surface the refresh-as-PR workflow below will use. It previously had fetch/transform/write but no validate stage. Builder architecture and a copy-able template: [#14](https://github.com/QuantEcon/data-lectures/issues/14)
- [x] Scheduled refresh workflow for dynamic datasets — **landed 2026-09-01** as `.github/workflows/refresh-snapshots.yml`, manifest-driven rather than cron-per-class: a weekly run asks `scripts/snapshots.py due` which `dynamic-snapshot` datasets have their cadence elapsed (or are `diverged`, or were never refreshed), runs each builder in place, stamps the manifest (`retrieved`, `sha256`, `integrity.upstream: verified`, `date_range.end`), regenerates the catalog, and opens a PR on `refresh/<stem>` whose body is the builder's overlap summary. Nothing auto-merges; the first consumer is `business_cycle_data.csv`, not UNRATE — the pilot's order inverted once the World Bank file turned out to be the one already here
- [x] Weekly sources-alive canary: fetch + validate, no commit, opens an issue on failure — **landed 2026-09-01** as the `canary` job of the same workflow: every dynamic snapshot's builder runs with `--out-dir`, and a failure opens or updates one `upstream-break` issue classified by exit code (2 = the data broke the contract, a human; anything else = the fetch, a retry). Covers the live APIs only as their snapshot twins land here — the 23 live-API lectures without a twin are still guarded by nothing but their own CI
- [ ] Consumer fan-out: a merged refresh or in-place correction dispatches rebuilds of the repos in the dataset's machine-readable `consumers` list — **policy recorded 2026-09-01** (AGENTS.md "Refresh, break, or schema change": per-consumer `on_refresh: rebuild | review`), and the refresh PR body already lists what the fan-out would do; the dispatch itself waits for the first snapshot with a consumer
- [ ] Package the refresh job as a reusable workflow (`quantecon/actions`) once it stabilizes

### Phase 6 — Metadata backfill for existing holdings

- [x] Manifest per dataset for the files now in `lectures/`: source, license, retrieval date, schema, consumers, provenance class. Schema sketched in `manifest-schema.yml` (Phase 2); backfill is per-file work gated on the license check below. **Complete 2026-09-01** — 41 datasets, 41 manifests; the last was `business_cycle_data.csv`, and the two `business_cycle` `.md` dumps left `lectures/` for `provenance/` the same day (`business_cycle_info.md` and `business_cycle_metadata.md` are prose, not datasets, so the gap is 1 file and not 3)
- [x] Classify: the 8 static intro files are author-assembled or verbatim; `business_cycle_data.csv` is the one dynamic snapshot — `class: dynamic-snapshot`, `cadence: annual`, declared 2026-09-01
- [ ] Licence check **per source**, not per file: the question is *"may this source be cached and served publicly, with attribution?"* — a cheap binary gate (`redistribution: permitted | restricted`, see AGENTS.md "Licensing and attribution"), a fast yes for public data sources. Two sources already answered: World Bank is **CC BY-4.0** (`business_cycle_metadata.md`, the model for what a manifest should capture) and RAM Legacy is **CC BY 4.0** (established against its Zenodo DOI record, P1). The remaining sources need the equivalent established by hand

  **Licensing does not gate migration** (settled 2026-08-06, [#35](https://github.com/QuantEcon/data-lectures/issues/35)). Inherited data — anything the lecture repos already serve publicly — migrates with its licence recorded **as found**, including `redistribution: restricted` and `name: null` where that is the honest answer. Moving the same bytes to a canonical host with better provenance and an explicit licence field improves on the status quo, so the migration does not wait on review; what needs further thought is tracked in [#35](https://github.com/QuantEcon/data-lectures/issues/35) with alternatives, and resolved before this repo is ever promoted as a branded public open-data host. That promotion is the gate, not each file's move — and with the custom domain deferred indefinitely (2026-08-12, D11), no such promotion is scheduled: the #35 inventory stays open and the gate binds only if a public host is someday established after all. This generalises the exception AGENTS.md already carried for `countries.csv`, and applies to **inherited** data only — a genuinely new dataset still establishes its licence before it lands
- [x] Keep-or-drop decision for the files with no consumer anywhere — **dropped 2026-07-16** in the Phase 2 restructure, rather than promoting them into the published namespace:
  - `GDP_per_capita_world_bank.csv` and `Metadata_Country_API_NY.GDP.PCAP.CD_DS2_en_csv_v2_4770417.csv` — an org-wide code search returns **zero** references to either, they are freely re-downloadable from the World Bank, and their licence was never established. Rehosting a stale snapshot nobody reads is the opposite of this repo's purpose
  - `fig_3.ods` — confirmed to carry no provenance the published `.xlsx` lacks: both parse to a single `Sheet1` of identical shape (34×6) and `DataFrame.equals` returns true, so it is a pure format twin
  - All three remain recoverable from git history

### Phase 7 — Data integrity verification

Verify that what this repo holds is actually the data it claims to be — against upstream sources, and against the copies lectures consume today — before any lecture is repointed here.

- [ ] **Byte-compare against the in-use copies**: each file migrated in Feb 2025 must be identical to the copy `lecture-python-intro` currently consumes (git blob hash compare). If a copy diverged, a repoint silently changes lecture output — this check is a hard prerequisite for Phase 8. Recorded **in the repoint PR** as a one-time gate, reproducible later from the manifest's `sha256` — not a manifest field (P1 decision)
- [ ] **Verbatim files**: re-fetch from the upstream source and compare (e.g. `mpd2020.xlsx` against the published Maddison Project 2020 release); record `sha256`, `status`, what it was compared `against`, and the date in the manifest's `integrity.upstream`
- [x] **Constructed / dynamic files**: re-run the committed builder (`builders/business_cycle.py` → `business_cycle_data.csv`) and confirm values agree in the overlap window with the committed snapshot — **done 2026-09-01, and they do not agree, by design**: the World Bank revised 236 of 320 overlap cells (max 1.5 pp) and appended two years. Recorded as `diverged` / `upstream-moved` in the manifest and in the register at [#39](https://github.com/QuantEcon/data-lectures/issues/39); the finding is what set the builder's 5 pp overlap bound
- [ ] **Author-assembled files** (the French Revolution spreadsheets, `caron.npy`, `nom_balances.npy` — prose-only provenance): spot-check key values against the cited publication and record what was checked; full verification may be impossible, and the manifest should say so (`status: unverifiable` with a one-line `note` — the honest known status, per P1)
- [ ] **Unverifiable or failing files**: flag in the manifest and open an issue — do not promote a file to the canonical URL namespace with a known-bad or unknown integrity status

### Phase 8 — Pilot deployment (meta#338)

The first end-to-end deployment: one dataset per hosting pattern, each the hardest representative of its class, carried through the full chain — layout, manifest, integrity check, publish, lecture repoint. Validates the convention empirically before anything is written into a standard. Sequence P1 → P2 → P3 → P4, each a small PR set (data repo + consuming lecture repos).

- [x] **P1 — local-path static**: `lingcod_msy_recovery.csv` (`msy_fishery`, intro). Tests: single-PR green build under `-nW`, Colab-unchanged download, catalog metadata for an author-assembled file. **Complete 2026-07-17** — data half #12, repoint QuantEcon/lecture-python-intro#792 (lecture build green in the single repoint PR); served URL verified byte-identical to the manifest `sha256`; Colab holds by construction (the lecture now reads a public URL, where the old relative path was exactly what broke downloaded notebooks); metadata findings recorded in meta#338. **The repo is live from this merge** — the pyodide/CORS check below remains open
- [x] **P2 — cross-series shared static**: the `pandas_panel` trio (`realwage.csv`, `countries.csv`, `employ.csv`), consumed by programming **and** python.myst. Tests: flat namespace with two consuming series, one data PR updating two lecture repos; retires 5 of the 8 legacy-repo references as a side effect. **Complete 2026-07-17** — data half #17, repoints QuantEcon/lecture-python-programming#578 and QuantEcon/lecture-python.myst#973; both lecture repos' own stale copies deleted in the repoint PRs. Lifecycle recorded in `migration.yml`
- [x] **P3 — external-repo static, LFS → plain git**: the `heavy_tails` set (Forbes ×2, cities ×2) plus the SCF pair from `high_dim_data`. **Complete 2026-08-11. Reframed 2026-08-07** — the Phase 3 storage decision made the published tree 100% plain git, so P3's original tests ("served URL makes the raw-vs-media trap invisible", "Pages handles LFS objects with `lfs: true`") are unrunnable by construction. What P3 now tests: the **host migration** off `media.githubusercontent.com` (repoint rule 6) across four consuming repos, two of which no CI can see; per-path LFS confined to `sources/`; and builders (`webscrape_forbes.ipynb`, `generating_mini.md`) migrating alongside their data. Note P3 **deletes nothing** — neither `intro` nor `wasm` holds a copy of the six files, and archiving `high_dim_data` preserves serving on both hosts, so rule 3's phase 2 does not apply and the set is fully reversible.

  **Data half complete 2026-08-10** — [#62](https://github.com/QuantEcon/data-lectures/pull/62) landed the six datasets, six manifests at `consumers: []`, six `migration.yml` records at `landed` and both frozen builders; [#63](https://github.com/QuantEcon/data-lectures/pull/63) landed `sources/SCF_plus.dta` and the `sources/` hash gate. All six verified byte-identical to the upstream LFS objects and confirmed serving real bytes (not pointer text) from `raw` and Pages, with the media host now 404ing for them — rule 6 confirmed in production.

  **Consumer half complete 2026-08-11**, in the order the ordering constraint required: C0 (QuantEcon/lecture-intro.zh-cn#291, seven `# i18n` markers) → C1 (QuantEcon/lecture-intro.zh-cn#292, zh-cn's 7 repoints) → C2 (QuantEcon/lecture-python-intro#832, QuantEcon/lecture-wasm#60, QuantEcon/test-actions-lecture-intro#53, three independent branches) → the flip ([#69](https://github.com/QuantEcon/data-lectures/pull/69)) → dashboard cleanup ([#70](https://github.com/QuantEcon/data-lectures/pull/70)). `high_dim_data` was then **archived, not deleted**, and still serves on both hosts. Independently validated in a fresh session against QuantEcon/workspace-lectures#36: the consumer set was complete (an org-wide tarball-and-content sweep of all 277 repos found no fifth consumer), all six datasets verify three-way byte-for-byte, and every dataset-driven figure on the live intro site is pixel-identical to the prior publish.

  **The flip was the acceptance test, and it measured as one.** Dry-run locally in both directions before pushing: `landed` → exit 1 with 6 warnings; `repointed` → exit 0. So the red window was real, opened when the last consuming PR merged, and closed with the flip. **Do this both-directions dry-run on every future wave** — it converts "same-day, trust me" into a measurement.

  Five things P3 proved that were not on its test list. A `constructed` dataset's builder must land in the **same** PR as the data, because `check_consumed_files.py` asserts the `builder:` path resolves. `builders/README.md`'s coverage table is a real coverage report and goes stale silently. The plain-git decision costs ~10 MB of packed history for 110 MB of working tree, since CSV compresses 5-22×. The **C0 → C1 → C2 ordering worked and proved less than it looks like** — the sync PR it was designed to defuse (QuantEcon/lecture-intro.zh-cn#293) touched zero data-read lines, zero `# i18n` markers and zero protected localisations, but nothing ever asked the model to rewrite those cells, so the markers remain unexercised, prompt-level protection and **the hand-diff is what protects a localisation**. And the translation sync is **`.md`-only**, so no hand-localised `_static` asset can be created, updated or repaired by it — every `data.ipynb` copy had to be repointed by hand in all four repos, filed upstream as QuantEcon/action-translation#271
- [ ] **P4 — dynamic snapshot twin**: originally `UNRATE` alone; **reframed 2026-09-01** as the `business_cycle` set, because the lecture that needs a twin is excluded from `lecture-wasm` for want of one and a partial twin buys it nothing. Done so far: `business_cycle_data.csv` manifested and its builder retrofitted ([#109](https://github.com/QuantEcon/data-lectures/pull/109)); the refresh-as-PR and canary workflow ([#110](https://github.com/QuantEcon/data-lectures/pull/110)); the first real refresh ([#112](https://github.com/QuantEcon/data-lectures/pull/112)); the World Bank set extended to three tables and the FRED half landed as one composite monthly file on a shared `builders/_fred.py` library ([#114](https://github.com/QuantEcon/data-lectures/pull/114)). Remaining: the `lecture-wasm` adoption ([QuantEcon/lecture-wasm#70](https://github.com/QuantEcon/lecture-wasm/issues/70) — intro keeps its live calls as the lesson), the flip with `on_refresh: rebuild`, and a canary run catching an induced failure
- [ ] Verify each migrated URL with a pyodide/JupyterLite fetch (CORS, meta#143)
- [ ] Fold every validated decision into the draft `styleguide/datasets.md` (manual#108) as it is proven

### Phase 9 — Adoption (broad sweep — the step that stalled in Feb 2025)

- [x] Repoint the remaining consuming lectures as datasets land here (data#4) — **done 2026-08-18**: all 40 static datasets in the corpus are migrated and `repointed` (tracks A–D above; the last four landed in [#98](https://github.com/QuantEcon/data-lectures/pull/98) and flipped in [#99](https://github.com/QuantEcon/data-lectures/pull/99)). The "Repoint rules" stay binding on any future wave: repoint all consumers of a dataset together, and never delete a copy a sibling repo reads
- [x] Remove lecture repos' duplicate copies as each repoint merges — **done 2026-09-01** (Track X, [QuantEcon/workspace-lectures#57](https://github.com/QuantEcon/workspace-lectures/issues/57)): 23 audit orphans plus 46 translation copies deleted across twelve repos, one PR each; the wasm mirror copies went only after wasm read data-lectures directly
- [ ] Intake rule for migrations: constructed datasets arrive **with their builders**; of the 5 known constructed-but-unscripted files, three arrived with recovered builders in Track C (`fred_data.csv` and the two `bbh` extracts — see `builders/README.md`); `hansen_jagannathan_1991_data.json` and `acs_data_summary.csv` still have none — recorded as QEP follow-ups per meta#338
- [ ] Graduate the convention to a QEP and merge manual#108, with the remaining sweep as its rollout checklist

## Open decisions (owned by meta#336 / manual#108, not this repo)

| Decision | Current strawman |
| --- | --- |
| Repo name | **settled 2026-07-16**: renamed `data-lectures` (Phase 1) |
| URL form | **settled 2026-08-12** (D11): lecture code reads `qeld.url('<filename>')`; the direct forms are the runtime-dependent raw URLs (repoint rule 5), standing rather than interim. `data.quantecon.org` deferred indefinitely ([#37](https://github.com/QuantEcon/data-lectures/issues/37)) |
| Layout | flat |
| Licensing review | per-source cache-and-serve-with-attribution gate (`redistribution: permitted \| restricted`), recorded in the manifest — this repo is a stability cache, not a content host |

When one of these settles, update this PLAN and `AGENTS.md` in the same PR that acts on it.
