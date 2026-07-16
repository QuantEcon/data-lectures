# AGENTS.md — working in QuantEcon/data-lectures

Guidance for coding agents (and humans) making changes in this repository. Read `PLAN.md` first — it holds the roadmap and links to the governing issues; this file holds the rules and traps.

## What this repo is

The canonical home for **data consumed by the QuantEcon lecture series** (renamed from `QuantEcon/data` on 2026-07-16, per [meta#336](https://github.com/QuantEcon/meta/issues/336)). It is **mid-transition**: the current tree is a legacy consumer-keyed layout (`lecture-python-intro/…`) that will become a flat published tree served at `https://data.quantecon.org/lectures/`. The full convention lives in the draft manual page ([QuantEcon.manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108)).

## Rules

### Layout

- Do **not** add new consumer-keyed directories (no `lecture-xyz/` folders). New datasets go in the flat published tree; if the restructure (PLAN Phase 2) hasn't landed yet, put new files where the pilot ([meta#338](https://github.com/QuantEcon/meta/issues/338)) is landing them and note it in the PR.
- No folder may imply ownership by a lecture series — any lecture can consume any file.

### Every dataset needs a class and a manifest

Classify as exactly one of:

| Class | Meaning | Must ship with the file |
| --- | --- | --- |
| **verbatim** | third-party file republished as distributed | source URL, citation, license, retrieval date |
| **constructed** | built from upstream sources by our processing | all of the above **plus the builder script, committed here** |
| **dynamic snapshot** | constructed, tracking a moving source (FRED, World Bank) | all of the above **plus a refresh cadence** |

A constructed dataset without its committed builder is a bug. Manifest fields: `source`, `license`, `retrieved`, `schema`, `consumers` (repo + lecture file, machine-readable), `maintainer`, `cadence` (dynamic only).

#### Two inherited-file states that look like violations but are tracked, not hidden

The Feb 2025 migration left files that cannot fully satisfy the rules above. The manifest records each gap **explicitly** — visible in the generated catalog — rather than burying it by misclassification. Both are provisional decisions from the P1 pilot ([meta#338](https://github.com/QuantEcon/meta/issues/338)), to be folded into [manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108).

- **`retrieved: null` — inherited-undated bytes.** `retrieved` is required, but may be `null` when the bytes were inherited (e.g. from a lecture repo) with **no recorded upstream-retrieval date**. Do **not** reconstruct one from git history — that records when QuantEcon acquired the file, not when it was retrieved from the source, and the false precision is worse than an honest null. A null `retrieved` must be paired with an `integrity.upstream` entry that says why (`status: unverifiable` with a reason).
- **`builder_status: unrecovered` — constructed without a recoverable builder.** A constructed dataset ships its builder, and one that omits it *silently* is the bug. Several inherited files are constructed with no recoverable extraction steps (PLAN Phase 9 tracks them). Keep `class: constructed` — reclassifying to `verbatim` to dodge the rule is misclassification — set `builder: null` and `builder_status: unrecovered`, and the gap stays visible for Phase 9 to recover. `unrecovered` is for **inherited files only**; never introduce a *new* constructed file without its builder.

### Corrections vs vintages

- **Corrections** (bad parse, wrong units, corrupt rows): fix **in place**, same filename — every consumer should get the fix. Use the manifest's `consumers` list to know which lectures to rebuild/review.
- **New vintages** (e.g. Maddison 2020 → 2023): **new filename** — the old vintage stays valid; consumers opt in.
- Never delete or rename a published file without checking `consumers` (and, until manifests are backfilled, grepping the lecture repos).

### URL forms — the LFS trap

When writing or reviewing URLs that fetch from this repo (in docs, tests, or lecture repoints):

| Form | LFS-tracked file | plain-git file |
| --- | --- | --- |
| `raw.githubusercontent.com/…` | ❌ returns pointer text | ✅ |
| `github.com/{org}/{repo}/raw/{ref}/…` | ✅ | ✅ |
| `media.githubusercontent.com/media/…` | ✅ | ❌ 404 |

- Interim safe form (works regardless of storage): `https://github.com/QuantEcon/data-lectures/raw/main/<path>`
- Final form once Pages is live: `https://data.quantecon.org/lectures/<filename>`
- Never reference a non-default branch in a published URL.

### LFS

- LFS is **per-path**, opt-in, large binaries only. Never add a blanket rule like `*.csv filter=lfs`.
- Do not LFS-track an **existing** file until you've confirmed no consumer fetches it via `raw.githubusercontent.com` — converting silently turns their download into a pointer file.
- The Pages deploy workflow must checkout with `lfs: true` or it publishes pointer files.

### Dynamic builders

Builders follow four stages — **fetch → pre-process → validate → write** — and only write on validation pass (expected columns/dtypes, row-count floor, recency of date range, no all-NaN columns, values unchanged in the overlap window with the previous vintage). Lectures always read the last-good snapshot: an upstream outage may fail a refresh, it must never break a lecture build.

### Live APIs

Live API calls are for *teaching data access*, not for getting data. Don't propose "the lecture should just call the API" as a fix — the fix is a snapshot here plus an automated refresh.

### Licensing

Before adding any file, confirm the upstream license permits redistribution and record it in the manifest. This repo is on track to be a promoted public host; unlicensed rehosting is a blocker, not a nice-to-have.

## Cross-repo hygiene

- Changes here often pair with PRs in lecture repos and issues in `QuantEcon/meta`. In commit messages and PR bodies, **never place a GitHub closing keyword (`fixes`, `closes`, `resolves`, …) immediately before a cross-repo reference** like `QuantEcon/meta#336` — GitHub will auto-close the referenced issue when the commit lands on the default branch. Write "See QuantEcon/meta#336" or "Part of QuantEcon/meta#336".
- When a decision marked **(open)** in `PLAN.md` gets settled upstream, update `PLAN.md` and this file in the same PR that acts on it.

## Repo map

```
lectures/            # the published tree — flat, served at data.quantecon.org/lectures/
                     #   9 datasets + business_cycle's upstream metadata dumps
                     #   manifests live here as sidecars: <filename>.yml
scripts/             # builders — NOT published
  business_cycle.py  #   writes business_cycle_data.csv into lectures/
manifest-schema.yml  # per-dataset manifest schema (strawman)
requirements.txt
PLAN.md              # roadmap — start here
AGENTS.md            # this file
```

The Feb 2025 consumer-keyed layout (`lecture-python-intro/{static,dynamic,scripts}/`) was flattened into this tree on 2026-07-16, while nothing referenced the repo.

**That freedom is now spent.** The restructure was free only because zero lectures pointed here; as soon as the first repoint merges (PLAN Phase 8), every move or rename in `lectures/` is a breaking change for a live lecture build. From that point on, treat published filenames as an API: corrections in place, new vintages under new names, and check `consumers` before touching anything.
