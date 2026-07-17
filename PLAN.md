# PLAN — `data-lectures` (formerly `QuantEcon/data`)

**Status:** active roadmap (last updated 2026-07-16)

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

## Phases

Ordering note: phases 1–3 and 6 can proceed now; phase 4 needs the DNS question resolved; phase 5 follows layout, **except its go-live guardrails, which must precede the first repoint**; phase 7 needs the sources recorded in phase 6; phase 8 (the pilot) is the first end-to-end pass through phases 2–7's machinery and requires phase 7's byte-compare for the files it touches **plus phase 5's go-live guardrails** — the first repoint turns `raw/main` into a production URL, so the repo must not go live unprotected; phase 9 follows the pilot (interim URL form makes repoints churn-tolerant to start earlier).

### Phase 0 — Scaffolding (this PR)

- [x] `PLAN.md` (this document)
- [x] `AGENTS.md` — conventions and gotchas for agents/contributors working here
- [x] README rewrite: purpose, routing rule, how to add a dataset, links to manual page

### Phase 1 — Identity ✅ (2026-07-16)

- [x] Rename `QuantEcon/data` → `data-lectures` (GitHub redirects preserve all existing URLs, so this was non-breaking)
- [x] Add repo description and topics (`quantecon`, `datasets`, `economics`, `open-data`, `teaching-materials`)

### Phase 2 — Layout (2026-07-16 — catalog outstanding)

- [x] Restructure consumer-keyed tree → flat published tree — `lectures/` is the published root; no folder implies series ownership. Done while zero lectures referenced the repo, so no consumer could break; **that window is now closed**
- [x] Decide where non-published assets live relative to the published tree — `scripts/` and `manifest-schema.yml` sit at the root, outside `lectures/`, and are never served. Manifests are the exception: they live *inside* `lectures/` as sidecars named `<filename>.yml`, so a dataset cannot be moved or removed without its metadata, and CI can assert the pairing with a glob
- [ ] Generate an index/catalog page from the manifests — doubles as the dataset registry

The sidecar naming uses the **full filename** (`mpd2020.xlsx.yml`, not `mpd2020.yml`) because a stem-keyed sidecar collides when one dataset ships in two formats — exactly the `fig_3.xlsx` / `fig_3.ods` case this repo already had. Strawman until the pilot tests it; see `manifest-schema.yml`.

### Phase 3 — Storage

- [ ] Per-path LFS via `.gitattributes` — large binaries only, small teaching files plain git (data#1; avoid `high_dim_data`'s blanket `*.csv` rule)
- [ ] Fold in `high_dim_data` content (data#2; coordinate with meta#337 for consuming-lecture repoints and the branch-only SCF file)

**Sequencing constraint:** enabling LFS breaks every `raw.githubusercontent.com` URL for the paths it covers (pointer files). Do not LFS-track existing files until consumers use a URL form that survives it (`github.com/{org}/{repo}/raw/{ref}/…` interim, or Pages final).

### Phase 4 — Publishing

- [ ] GitHub Pages deploy of the published tree, **`lfs: true` at checkout** (else pointer files publish)
- [ ] `data.quantecon.org` DNS + custom domain (an old NestJS box on AWS Sydney currently answers this name — investigate before repointing)
- [ ] Verify `access-control-allow-origin: *` on served files (pyodide/JupyterLite, meta#143)
- [ ] Monitor Pages soft limits (~1 GB site, 100 GB/month)

### Phase 5 — Automation (`.github/`)

**Go-live guardrails** — the minimal subset that must precede the first repoint (Phase 8); the rest of this phase follows at its own pace:

- [x] Branch protection on `main`: PRs required (no direct pushes; zero approvals so a solo maintainer can still merge), force-pushes and deletion blocked. Once a lecture repoints, `raw/main` is a production URL and an accidental force-push is a lecture outage (ruleset added 2026-07-17)
- [x] Minimal consumed-file check: CI that asserts every file in `lectures/` whose manifest has a non-empty `consumers` list still exists and matches its manifest `sha256` — the narrowest possible test that a PR cannot break a live lecture. Subsumed later by the full PR validation below (added 2026-07-17: `.github/workflows/consumed-file-check.yml`)

Full automation:

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

- [ ] **P1 — local-path static**: `lingcod_msy_recovery.csv` (`msy_fishery`, intro). Tests: single-PR green build under `-nW`, Colab-unchanged download, catalog metadata for an author-assembled file
- [ ] **P2 — cross-series shared static**: the `pandas_panel` trio (`realwage.csv`, `countries.csv`, `employ.csv`), consumed by programming **and** python.myst. Tests: flat namespace with two consuming series, one data PR updating two lecture repos; retires 5 of the 8 legacy-repo references as a side effect
- [ ] **P3 — external-repo static with LFS**: the `heavy_tails` set (Forbes ×2, cities ×2) plus the SCF pair from `high_dim_data`. Tests: served URL makes the raw-vs-media LFS trap invisible, Pages handles LFS objects (`lfs: true`), builders (`webscrape_forbes.ipynb`, `generating_mini.md`) migrate alongside their data
- [ ] **P4 — dynamic snapshot twin**: `UNRATE`, consumed today by 4 lectures across 3 repos via 2 access methods. Tests: the full dynamic template — manifest, four-stage builder, refresh-as-PR, canary catching an induced failure — plus the documented live-call ↔ snapshot switch mechanism
- [ ] Verify each migrated URL with a pyodide/JupyterLite fetch (CORS, meta#143)
- [ ] Fold every validated decision into the draft `styleguide/datasets.md` (manual#108) as it is proven

### Phase 9 — Adoption (broad sweep — the step that stalled in Feb 2025)

- [ ] Repoint the remaining consuming lectures as datasets land here (data#4) — mechanical once the pilot proves the convention (~25 files beyond the pilot set)
- [ ] Remove lecture repos' duplicate copies as each repoint merges (tracked with the orphan sweep in meta#337)
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
