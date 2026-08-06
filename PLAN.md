# PLAN — `data-lectures` (formerly `QuantEcon/data`)

**Status:** active roadmap (last updated 2026-08-06) — **the repo is LIVE**: the first repoint merged 2026-07-17 (P1, `lingcod_msy_recovery.csv` → `msy_fishery`), so published filenames are an API from here on

**Where the numbers stand (audit dashboard, 2026-08-06):** 10 of 41 static datasets migrated and repointed, 31 to go; 22 lectures still fetch live API data; 35 committed orphans; 0 legacy-repo references; 5 URL forms in use.

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
| [QuantEcon/workspace-lectures#14](https://github.com/QuantEcon/workspace-lectures/issues/14) | Session work plan: pilot kickoff sequencing (meta#337 risks → P1 → P2) |

## Where we are

**Update 2026-07-16 — the layout below has been flattened (Phase 2).** The 8 in-use static files and `business_cycle_data.csv` now sit directly in `lectures/`; `scripts/` moved to the root; the 3 no-consumer files were dropped (see Phase 6). The audit that follows is retained as the record of what was migrated and what state each file was in — it is the input to Phases 6 and 7, and the `consumers` column of the manifests still has to be backfilled from it.

### The audit (2026-07-15)

- 12 data files for `lecture-python-intro` under a **consumer-keyed layout** (`lecture-python-intro/{static,dynamic,scripts}/`), in three distinct states:
  - **8 duplicates of data in active use** — `mpd2020.xlsx`, `longprices.xls`, `chapter_3.xlsx`, `assignat.xlsx`, `dette.xlsx`, `fig_3.xlsx`, `caron.npy`, `nom_balances.npy` are consumed by intro lectures (`long_run_growth`, `inflation_history`, `french_rev`), but via intro's **own copies** (own-repo URLs, or local paths for the `.npy` pair) — these are the Phase 8 repoint targets
  - **2 dead on both ends** — the World Bank GDP-per-capita CSV and its metadata twin are orphaned in intro too; nothing reads either copy anywhere
  - **2 never adopted** — `business_cycle_data.csv` (the one dynamic snapshot; intro's `business_cycle` still fetches live from wbgapi/FRED) and `fig_3.ods` (a source-format twin of `fig_3.xlsx`, referenced by nothing)
- one manual refresh script (`scripts/business_cycle.py`), run by hand — it has fetch/transform/write but **no validate stage**
- **no `.github/`** — no CI, no PR validation, no scheduled refresh
- no LFS, no per-dataset manifests, no license records
- referenced by **zero lectures** (confirmed by the audit and by live GitHub code search, 2026-07-16) — the Feb 2025 migration (data#5–#7) landed the files but the repoint (data#4) never happened. Until the first repoint merges, everything here can be restructured freely

## Where we're going (per the draft convention)

- **Flat published tree** served at `https://data.quantecon.org/lectures/<filename>` via GitHub Pages (custom domain), CORS-open for pyodide/JupyterLite
- Every dataset classified **verbatim / constructed / dynamic snapshot**, each with a manifest — authoritative field reference in `manifest-schema.yml`, as revised by the P1 pilot (`integrity`, `builder_status`, `known_nulls` and `license.verified` joined the original sketch of `source` / `license` / `retrieved` / `schema` / `consumers` / `maintainer` / `cadence`)
- Constructed and dynamic datasets ship their **builder**; dynamic datasets get **scheduled refresh-as-PR** plus a weekly **sources-alive canary**
- Per-path LFS for large binaries only; storage choice invisible to consumers because URLs decouple from hosting

## Repoint rules

Five rules learned the hard way, three of them the hard way twice. Rules 1-3 are about *ordering* and none is enforced by CI — the strict audit catches rule 2 only after the fact, and cannot see rule 3 at all. Rule 4 is about *scope*, and rule 5 about *URL form*.

### 1. Repoint a sibling reader before deleting the file it reads

`lecture-wasm` mirrors `lecture-python-intro`'s sources and fetches intro's **committed blobs** by URL — e.g. `long_run_growth.md` reads `raw.githubusercontent.com/QuantEcon/lecture-python-intro/main/lectures/datasets/mpd2020.xlsx`. Deleting intro's copy in the repoint PR therefore 404s the wasm build immediately.

So the general rule "delete the lecture repo's own copy in the same repoint PR" holds **only** when no sibling reads that copy. Where one does, the sibling's repoint must land **first or together**, and the deletion goes in the same set — never in an earlier PR with the sibling's fix scheduled later.

This affects every `intro` + `wasm` dataset, which is all 16 of the multi-consumer files below.

### 2. Repoint every consumer of a dataset together

The strict audit has **no green state for a partially-repointed dataset**. `scripts/build_audit.py` fails a record marked `pending`/`landed` while any consumer already reads data-lectures, *and* fails one marked `repointed`/`final` while any consumer still does not. That is deliberate — it is what makes the tracker trustworthy — but it means a dataset with two consuming repos cannot be moved one repo at a time without the drift alarm firing in the gap.

**16 of the 31 remaining datasets have two consuming repos, and every one of them is `lecture-python-intro` + `lecture-wasm`.** There is no other cross-series coupling left; the last one was the P2 `pandas_panel` trio, already done.

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

A repo that publishes on push needs no split. Neither does deleting a copy that **no lecture reads in either repo** — typically one a repo committed alongside its mirrored sources while the lecture itself fetches the *other* repo's copy by URL (a *mirror-orphan*); `lecture-wasm` holds a dozen of these.

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
| Browser — `lecture-wasm` code-cell reads | `raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/<file>`, or `media.githubusercontent.com/media/…` for LFS-tracked files |

`{download}` targets and prose links are plain navigations — CORS does not apply, and the `github.com` form is fine there. The audit classifies references by org/repo across all URL forms, so both spellings count as the same pattern — but the strict build now also checks the *form*: any `lecture-wasm` code-cell read via a `github.com/…` URL fails the audit. That is a **post-merge net, not a gate** — the scan reads each lecture repo's `main`, so a violation turns the dashboard red at the next audit run rather than blocking the offending PR; the repoint PR remains the place the rule is actually upheld. Quick test from any `quantecon.github.io` page console: `fetch('<url>')` — the bad form rejects, the good form resolves.

Phase 4 inherits the requirement: `data.quantecon.org` must serve `access-control-allow-origin: *` before `lecture-wasm` can cut over to it — recorded as an acceptance criterion on [#37](https://github.com/QuantEcon/data-lectures/issues/37).

## Migration tracks

The remaining work decomposes by **consuming series** rather than by hosting pattern, because — apart from the `intro`/`wasm` pairing — each series now owns its own data. This is the execution view; the phases below remain the machinery each track passes through.

| Track | Datasets | Coupling | Blocked on |
| --- | --- | --- | --- |
| **A — `intro` + `wasm`** | 17: the 8 landed intro statics, the 6 `high_dim_data` files, `life-expectancy…`, `usa-gini…`, `graph.txt` | **paired — repoint together, always** | nothing to start; `usa-gini` needs the SCF files first |
| **B — `python.myst`** | 7: `maketable1/2/4.dta`, `fp.dta`, `hansen_singleton_1982/1983_data.csv`, `NEWQDATA.csv` | none | nothing |
| **C — `advanced.myst`** | 6: `dataBHS.mat`, `acs_data_summary.csv`, `bbh` ×2, `fred_data.csv`, `hansen_jagannathan_1991_data.json` | none | nothing (builder recovery is in-wave work, not a gate) |
| **D — `programming`** | 1: `test_pwt.csv` | none | nothing — a single-PR track |
| **E — dynamic / live-API** | the UNRATE twin, then the 15 incidental API lectures | wasm is the forcing customer | [#14](https://github.com/QuantEcon/data-lectures/issues/14) schema decisions, [#26](https://github.com/QuantEcon/data-lectures/issues/26) fetch layer |
| **X — orphan sweep** | 35 committed orphans across 6 repos | per repo | that repo's repoints landing first |
| **Y — infra / cutover** | DNS → custom domain → interim-to-final URL sweep → QEP | — | an external infra answer on `52.64.86.66` |

`lecture-dp`, `lecture-jax` and `continuous_time_mcs` are **not data consumers** — dp's 10 committed files are inherited orphans, jax embeds `graph.txt` via `%%file`, and continuous_time_mcs has one orphan scratch file. They appear only in Track X.

**Tracks A–D are independent of each other and can run in any order or in parallel.** The only hard dependencies in the whole programme are: `usa-gini-nwealth-tincome-lincome.csv` is built from `SCF_plus_mini.csv` (so it follows the SCF migration inside Track A); Track E's rollout needs its own template proven first; Track X follows its repo's repoints; and Track Y's cutover is last.

Track Y is the one item with **external lead time** — it waits on whether `52.64.86.66` can be decommissioned, which is an infrastructure answer rather than a migration one. Worth starting that enquiry in parallel with the data work rather than at the end.

### Where this work happens

Repoints span data-lectures plus one or two lecture repos and must land together, which is exactly what [`QuantEcon/workspace-lectures`](https://github.com/QuantEcon/workspace-lectures) exists for: all the repos cloned side by side, `bin/foreach` for cross-repo greps and branch creation, and its stated pattern of *same branch in each repo → edit → commit per repo → one PR per repo*. `data-lectures` is already in its manifest. The artifacts still live here — this PLAN, the manifests, `migration.yml` — and every PR still lands in its own repo; the workspace is the bench, not the destination.

## Phases

Ordering note: phases 1–3 and 6 can proceed now; phase 4 needs the DNS question resolved; phase 5 follows layout, **except its go-live guardrails, which must precede the first repoint**; phase 7 needs the sources recorded in phase 6; phase 8 (the pilot) is the first end-to-end pass through phases 2–7's machinery and requires phase 7's byte-compare for the files it touches **plus phase 5's go-live guardrails** — the first repoint turns `raw/main` into a production URL, so the repo must not go live unprotected; phase 9 follows the pilot (interim URL form makes repoints churn-tolerant to start earlier).

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

- [ ] Add `sources/` for builder inputs, with `sources/README.md` as the **audit trail**: one row per committed file recording where it came from, when, its licence, the upstream identifier (DOI where one exists), its `sha256`, and which builder consumes it. A file in `sources/` is not a published dataset and gets no sidecar manifest — this README is its provenance record
- [ ] Per-path LFS via `.gitattributes`, scoped to `sources/` only — never a blanket rule like `high_dim_data`'s `*.csv` **and** `*.dta` (data#1)
- [ ] Fold in `high_dim_data` content (data#2; coordinate with meta#337 for consuming-lecture repoints)
- [ ] **Repoint `generating_mini.md`'s input URL.** The SCF builder currently reads its source over the network from the repo being retired — `pd.read_stata('https://github.com/QuantEcon/high_dim_data/blob/main/SCF_plus/SCF_plus.dta?raw=true')`. Archiving `high_dim_data` while that line stands re-introduces exactly the legacy-repo dependency this project drove to zero. Point it at `sources/` before archiving
- [ ] Set the Pages job's checkout to `lfs: false` once the above holds — nothing under `lectures/` is an LFS object, so the 99 MiB `.dta` never needs downloading on a dashboard build (it runs on every push to `main` plus weekly)

**Sequencing constraint** (still applies to anything that *does* enter LFS): enabling LFS breaks every `raw.githubusercontent.com` URL for the paths it covers — those URLs return pointer text, not data, so consumers fail with a confusing parse error rather than a 404. Do not LFS-track an existing file until its consumers use a form that survives it. Keeping the published tree plain-git means no consumer-facing path is ever affected.

### Phase 4 — Publishing

- [x] GitHub Pages deploy of the published tree, **`lfs: true` at checkout** (else pointer files publish) — landed 2026-07-17 with the audit dashboard (`.github/workflows/audit-dashboard.yml`, [#20](https://github.com/QuantEcon/data-lectures/issues/20)): the default `quantecon.github.io/data-lectures/` site serves the dashboard at `/` and the published tree at `/lectures/`. The custom domain below stays open
- [ ] `data.quantecon.org` DNS + custom domain (an old NestJS box on AWS Sydney currently answers this name — investigate before repointing)
- [x] Verify `access-control-allow-origin: *` on served files (pyodide/JupyterLite, meta#143) — **verified 2026-08-06**: `quantecon.github.io/data-lectures/lectures/lingcod_msy_recovery.csv` returns `access-control-allow-origin: *`. The requirement is met on the default Pages domain today and does **not** wait on the custom domain; re-verify once DNS moves
- [ ] Monitor Pages soft limits (~1 GB site, 100 GB/month)

### Phase 5 — Automation (`.github/`)

**Go-live guardrails** — the minimal subset that must precede the first repoint (Phase 8); the rest of this phase follows at its own pace:

- [x] Branch protection on `main`: PRs required (no direct pushes; zero approvals so a solo maintainer can still merge), force-pushes and deletion blocked. Once a lecture repoints, `raw/main` is a production URL and an accidental force-push is a lecture outage (ruleset added 2026-07-17)
- [x] Minimal consumed-file check: CI that asserts every file in `lectures/` whose manifest has a non-empty `consumers` list still exists and matches its manifest `sha256` — the narrowest possible test that a PR cannot break a live lecture. Subsumed later by the full PR validation below (added 2026-07-17: `.github/workflows/consumed-file-check.yml`, and made a **required status check** in the `protect-main` ruleset the same day — a red check blocks the merge)

Full automation:

- [x] Audit dashboard workflow ([#20](https://github.com/QuantEcon/data-lectures/issues/20), added 2026-07-17): `.github/workflows/audit-dashboard.yml` rebuilds the full-universe data audit + migration tracker from the 8 lecture repos' `main` (push to main / weekly / dispatch) and deploys it with the published tree to Pages. Strict mode fails the build on an unannotated data reference or a `migration.yml` status the scan contradicts
- [ ] PR validation: manifest schema check + per-dataset invariant tests (expected columns/dtypes, row-count floor, date-range recency, no all-NaN columns, overlap-window agreement with the previous vintage) on every PR touching data. The schema decisions these tests force — column patterns for wide files, `known_nulls` exact-vs-ceiling, a canonical dtype vocabulary — are researched in [#14](https://github.com/QuantEcon/data-lectures/issues/14)
- [ ] Retrofit `scripts/business_cycle.py` to the four-stage builder contract — it has fetch/transform/write today but **no validate stage**. Builder architecture and a copy-able template: [#14](https://github.com/QuantEcon/data-lectures/issues/14)
- [ ] Scheduled refresh workflow for dynamic datasets — cron per cadence class, runs the builder (fetch → pre-process → validate → write), lands the result as a PR whose diff summary (rows added, date-range delta, overlap-window changes) is the review surface; low-risk series may auto-merge on green (first consumer: the UNRATE pilot, meta#338 P4)
- [ ] Weekly sources-alive canary: fetch + validate, no commit, opens an issue on failure — relocates API fragility from 7 lecture repos' CI into one scheduled job here
- [ ] Consumer fan-out: a merged refresh or in-place correction dispatches rebuilds of the repos in the dataset's machine-readable `consumers` list
- [ ] Package the refresh job as a reusable workflow (`quantecon/actions`) once it stabilizes

### Phase 6 — Metadata backfill for existing holdings

- [ ] Manifest per dataset for the **9** files now in `lectures/`: source, license, retrieval date, schema, consumers, provenance class. Schema sketched in `manifest-schema.yml` (Phase 2); backfill is per-file work gated on the license check below
- [ ] Classify: the 8 static intro files are author-assembled or verbatim; `business_cycle_data.csv` is the one dynamic snapshot and needs its cadence declared
- [ ] Licence check **per source**, not per file: the question is *"may this source be cached and served publicly, with attribution?"* — a cheap binary gate (`redistribution: permitted | restricted`, see AGENTS.md "Licensing and attribution"), a fast yes for public data sources. Two sources already answered: World Bank is **CC BY-4.0** (`business_cycle_metadata.md`, the model for what a manifest should capture) and RAM Legacy is **CC BY 4.0** (established against its Zenodo DOI record, P1). The remaining sources need the equivalent established by hand

  **Licensing does not gate migration** (settled 2026-08-06, [#35](https://github.com/QuantEcon/data-lectures/issues/35)). Inherited data — anything the lecture repos already serve publicly — migrates with its licence recorded **as found**, including `redistribution: restricted` and `name: null` where that is the honest answer. Moving the same bytes to a canonical host with better provenance and an explicit licence field improves on the status quo, so the migration does not wait on review; what needs further thought is tracked in [#35](https://github.com/QuantEcon/data-lectures/issues/35) with alternatives, and resolved before `data.quantecon.org` is promoted as a public open-data host. That promotion is the gate, not each file's move. This generalises the exception AGENTS.md already carried for `countries.csv`, and applies to **inherited** data only — a genuinely new dataset still establishes its licence before it lands
- [x] Keep-or-drop decision for the files with no consumer anywhere — **dropped 2026-07-16** in the Phase 2 restructure, rather than promoting them into the published namespace:
  - `GDP_per_capita_world_bank.csv` and `Metadata_Country_API_NY.GDP.PCAP.CD_DS2_en_csv_v2_4770417.csv` — an org-wide code search returns **zero** references to either, they are freely re-downloadable from the World Bank, and their licence was never established. Rehosting a stale snapshot nobody reads is the opposite of this repo's purpose
  - `fig_3.ods` — confirmed to carry no provenance the published `.xlsx` lacks: both parse to a single `Sheet1` of identical shape (34×6) and `DataFrame.equals` returns true, so it is a pure format twin
  - All three remain recoverable from git history

### Phase 7 — Data integrity verification

Verify that what this repo holds is actually the data it claims to be — against upstream sources, and against the copies lectures consume today — before any lecture is repointed here.

- [ ] **Byte-compare against the in-use copies**: each file migrated in Feb 2025 must be identical to the copy `lecture-python-intro` currently consumes (git blob hash compare). If a copy diverged, a repoint silently changes lecture output — this check is a hard prerequisite for Phase 8. Recorded **in the repoint PR** as a one-time gate, reproducible later from the manifest's `sha256` — not a manifest field (P1 decision)
- [ ] **Verbatim files**: re-fetch from the upstream source and compare (e.g. `mpd2020.xlsx` against the published Maddison Project 2020 release); record `sha256`, `status`, what it was compared `against`, and the date in the manifest's `integrity.upstream`
- [ ] **Constructed / dynamic files**: re-run the committed builder (`scripts/business_cycle.py` → `business_cycle_data.csv`) and confirm values agree in the overlap window with the committed snapshot
- [ ] **Author-assembled files** (the French Revolution spreadsheets, `caron.npy`, `nom_balances.npy` — prose-only provenance): spot-check key values against the cited publication and record what was checked; full verification may be impossible, and the manifest should say so (`status: unverifiable` with a one-line `note` — the honest known status, per P1)
- [ ] **Unverifiable or failing files**: flag in the manifest and open an issue — do not promote a file to the canonical URL namespace with a known-bad or unknown integrity status

### Phase 8 — Pilot deployment (meta#338)

The first end-to-end deployment: one dataset per hosting pattern, each the hardest representative of its class, carried through the full chain — layout, manifest, integrity check, publish, lecture repoint. Validates the convention empirically before anything is written into a standard. Sequence P1 → P2 → P3 → P4, each a small PR set (data repo + consuming lecture repos).

- [x] **P1 — local-path static**: `lingcod_msy_recovery.csv` (`msy_fishery`, intro). Tests: single-PR green build under `-nW`, Colab-unchanged download, catalog metadata for an author-assembled file. **Complete 2026-07-17** — data half #12, repoint QuantEcon/lecture-python-intro#792 (lecture build green in the single repoint PR); served URL verified byte-identical to the manifest `sha256`; Colab holds by construction (the lecture now reads a public URL, where the old relative path was exactly what broke downloaded notebooks); metadata findings recorded in meta#338. **The repo is live from this merge** — the pyodide/CORS check below remains open
- [x] **P2 — cross-series shared static**: the `pandas_panel` trio (`realwage.csv`, `countries.csv`, `employ.csv`), consumed by programming **and** python.myst. Tests: flat namespace with two consuming series, one data PR updating two lecture repos; retires 5 of the 8 legacy-repo references as a side effect. **Complete 2026-07-17** — data half #17, repoints QuantEcon/lecture-python-programming#578 and QuantEcon/lecture-python.myst#973; both lecture repos' own stale copies deleted in the repoint PRs. Lifecycle recorded in `migration.yml`
- [ ] **P3 — external-repo static with LFS**: the `heavy_tails` set (Forbes ×2, cities ×2) plus the SCF pair from `high_dim_data`. Tests: served URL makes the raw-vs-media LFS trap invisible, Pages handles LFS objects (`lfs: true`), builders (`webscrape_forbes.ipynb`, `generating_mini.md`) migrate alongside their data
- [ ] **P4 — dynamic snapshot twin**: `UNRATE`, consumed today by 4 lectures across 3 repos via 2 access methods. Tests: the full dynamic template — manifest, four-stage builder, refresh-as-PR, canary catching an induced failure — plus the documented live-call ↔ snapshot switch mechanism
- [ ] Verify each migrated URL with a pyodide/JupyterLite fetch (CORS, meta#143)
- [ ] Fold every validated decision into the draft `styleguide/datasets.md` (manual#108) as it is proven

### Phase 9 — Adoption (broad sweep — the step that stalled in Feb 2025)

- [ ] Repoint the remaining consuming lectures as datasets land here (data#4) — **31 datasets**, organised as tracks A–D above. Mechanical, but see "Repoint rules": repoint all consumers of a dataset together, and never delete a copy a sibling repo reads
- [ ] Remove lecture repos' duplicate copies as each repoint merges (tracked with the orphan sweep in meta#337) — 35 orphans today, Track X. Note the wasm mirror copies are only safe to delete **after** wasm reads data-lectures directly, not before
- [ ] Intake rule for migrations: constructed datasets arrive **with their builders**; the 5 known constructed-but-unscripted files (`hansen_jagannathan_1991_data.json`, `fred_data.csv`, the two `bbh` extracts, `acs_data_summary.csv`) need their pipelines recovered or rewritten — recorded as QEP follow-ups per meta#338
- [ ] Graduate the convention to a QEP and merge manual#108, with the remaining sweep as its rollout checklist

## Open decisions (owned by meta#336 / manual#108, not this repo)

| Decision | Current strawman |
| --- | --- |
| Repo name | **settled 2026-07-16**: renamed `data-lectures` (Phase 1) |
| URL form | `data.quantecon.org/lectures/...`; interim `github.com/QuantEcon/data-lectures/raw/main/...` |
| Layout | flat |
| Licensing review | per-source cache-and-serve-with-attribution gate (`redistribution: permitted \| restricted`), recorded in the manifest — this repo is a stability cache, not a content host |

When one of these settles, update this PLAN and `AGENTS.md` in the same PR that acts on it.
