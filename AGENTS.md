# AGENTS.md — working in QuantEcon/data-lectures

Guidance for coding agents (and humans) making changes in this repository. Read `PLAN.md` first — it holds the roadmap and links to the governing issues; this file holds the rules and traps.

## What this repo is

The canonical home for **data consumed by the QuantEcon lecture series** (renamed from `QuantEcon/data` on 2026-07-16, per [meta#336](https://github.com/QuantEcon/meta/issues/336)). Its purpose is **stability**: it snapshots upstream sources — with attribution to each source carried in the manifest — so a lecture build never depends on a live API or a third-party host staying up. It is a **cache, not a content-distribution host**. The published tree is **flat** (`lectures/`, since 2026-07-16) and live on GitHub Pages; the remaining transition is the custom domain — files are served at `quantecon.github.io/data-lectures/lectures/` today and will move to `https://data.quantecon.org/lectures/` once DNS is resolved (PLAN Phase 4, [#15](https://github.com/QuantEcon/data-lectures/issues/15)). The full convention lives in the draft manual page ([QuantEcon.manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108)).

## Rules

### Layout

- Do **not** add new consumer-keyed directories (no `lecture-xyz/` folders). New datasets go directly in the flat published tree, `lectures/<filename>`, with their sidecar manifest beside them.
- No folder may imply ownership by a lecture series — any lecture can consume any file.

### Every dataset needs a class and a manifest

Classify as exactly one of:

| Class | Meaning | Must ship with the file |
| --- | --- | --- |
| **verbatim** | third-party file republished as distributed | source URL, citation, license, retrieval date |
| **constructed** | built from upstream sources by our processing | all of the above **plus the builder script, committed here** |
| **dynamic snapshot** | constructed, tracking a moving source (FRED, World Bank) | all of the above **plus a refresh cadence** |

A constructed dataset without its committed builder is a bug. Manifest fields: `source`, `license` (with the `verified` date it was established), `retrieved`, `integrity` (`sha256` plus the `upstream` verification status, see Phase 7), `schema` (including `known_nulls`), `consumers` (repo + lecture file, machine-readable), `maintainer`, `builder` / `builder_status`, `cadence` (dynamic only). `manifest-schema.yml` is the authoritative, commented field reference — keep it and this list in step.

**Verifying `integrity.upstream`, by class** (once here, not repeated per manifest): re-fetch-and-compare for **verbatim**; re-run the builder and compare the overlap window for **constructed / dynamic**; spot-check against the cited publication for author-assembled. When verification is impossible, say so plainly — `status: unverifiable` with a one-line `note` is a known status the catalog can show; silence is not. **Migration safety** (does the file byte-match what the consuming lecture used before a repoint?) is deliberately *not* a manifest field: it is a one-time gate recorded in the repoint PR, and the manifest's `sha256` keeps it reproducible afterwards.

**Capture what the source gives you; never let a missing field block a useful dataset.** Rich provenance — DOI, upstream version, exact retrieval date, licence id — is always welcome and worth recording whenever it is available, because it makes the data auditable years later at almost no ongoing cost. But effort scales with what the source actually provides: where a field is genuinely unavailable, record it as an explicit, reasoned gap (see the inherited-file states below) rather than fabricating it or refusing the file. A clean, well-documented source should produce a short manifest; only genuinely messy provenance earns a long one.

#### Two inherited-file states that look like violations but are tracked, not hidden

The Feb 2025 migration left files that cannot fully satisfy the rules above. The manifest records each gap **explicitly** — visible in the generated catalog — rather than burying it by misclassification. Both are provisional decisions from the P1 pilot ([meta#338](https://github.com/QuantEcon/meta/issues/338)), to be folded into [manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108).

- **`retrieved: null` — inherited-undated bytes.** `retrieved` is required, but may be `null` when the bytes were inherited (e.g. from a lecture repo) with **no recorded upstream-retrieval date**. Do **not** reconstruct one from git history — that records when QuantEcon acquired the file, not when it was retrieved from the source, and the false precision is worse than an honest null. A null `retrieved` must be paired with an `integrity.upstream` entry that says why (`status: unverifiable` with a `note`).
- **`builder_status: unrecovered` — constructed without a recoverable builder.** A constructed dataset ships its builder, and one that omits it *silently* is the bug. Several inherited files are constructed with no recoverable extraction steps (PLAN Phase 9 tracks them). Keep `class: constructed` — reclassifying to `verbatim` to dodge the rule is misclassification — set `builder: null` and `builder_status: unrecovered`, and the gap stays visible for Phase 9 to recover. `unrecovered` is for **inherited files only**; never introduce a *new* constructed file without its builder.

### Repointing a lecture — three ordering traps

All cheap to follow and expensive to discover. `PLAN.md` carries the reasoning and the current counts.

- **Never delete a file a sibling repo reads.** `lecture-wasm` fetches `lecture-python-intro`'s *committed blobs* by URL, so deleting intro's copy in a repoint PR 404s the wasm build immediately. "Delete the lecture repo's own copy in the same repoint PR" applies only where no sibling reads it; where one does, the sibling's repoint lands first or in the same set.
- **Repoint every consumer of a dataset together.** The strict audit has no green state for a partially-repointed dataset — `pending`/`landed` fails once any consumer reads data-lectures, and `repointed`/`final` fails while any consumer still does not. Land the lecture repoints first, then flip `migration.yml`; that flip is the push that re-runs the audit, so reality and the tracker agree by the time it runs. This binds the **lecture PRs too**: merging one half of a set while the other sits open opens the same window.
- **Repoint, publish, then delete — the published site lags `main`.** A lecture repo that publishes on a **tag** (`lecture-python-intro` uses `publish*`) does not refresh its site when a repoint merges, so the already-published notebooks keep the old URL. Delete the file in the same PR and that URL 404s for every reader who downloads or opens the lecture in Colab, until someone tags a publish. Rendered HTML is unaffected — figures are baked at build time — so nothing will alert you. **Split it: repoint the URLs and keep the files, publish, then delete in a follow-up PR.** Repos that publish on push to `main` (`lecture-wasm`) self-heal and need no split — and neither does deleting a copy that no lecture reads, such as one a repo committed while its lecture fetches another repo's copy by URL (a *mirror-orphan*).

Cross-repo repoints are worked from [`QuantEcon/workspace-lectures`](https://github.com/QuantEcon/workspace-lectures) — same branch name in each repo, one PR per repo, no aggregate PR.

### Repointing a lecture — one scope rule

- **A migration moves bytes; it does not update them.** Land the copy the lectures already consume, validated byte-identical — that is what makes a repoint provably unable to change a figure. If the committed file differs from what upstream publishes today, migrate it unchanged anyway, record the delta in `integrity.upstream` **and** in the register at [#39](https://github.com/QuantEcon/data-lectures/issues/39), and leave the decision for after the migration. Adopting a newer vintage changes lecture output and is an author's call, not an infrastructure one — and per "Corrections vs vintages" below it gets a **new filename**, never a silent replacement.

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

### LFS, and `sources/` vs `lectures/`

**The published tree is plain git. Do not put an LFS object in `lectures/`** (settled 2026-08-06, PLAN Phase 3). Every published dataset fits comfortably in plain git — the largest, `SCF_plus_mini_no_weights.csv`, is 72.4 MiB against GitHub's 100 MiB limit. Keeping it that way means **no consumer can ever hit the raw-vs-media trap above**; the hazard is removed rather than managed.

LFS exists here for one purpose: **upstream inputs that builders consume and no lecture reads**, which live in `sources/` and are never served.

- `lectures/<file>` — a published dataset. Plain git, sidecar manifest required, its filename is an API.
- `sources/<file>` — a builder input. Per-path LFS, **no** manifest, not served, recorded instead in `sources/README.md` — the audit trail: origin, retrieval date, licence, upstream identifier (DOI where one exists), `sha256`, and the builder that consumes it.

Rules that still apply:

- LFS is **per-path**, opt-in, large binaries only. Never a blanket rule like `high_dim_data`'s `*.csv` **and** `*.dta`.
- Do not LFS-track an **existing** file until you've confirmed no consumer fetches it via `raw.githubusercontent.com` — converting silently turns their download into pointer text.
- A builder must read its input from `sources/`, never over the network from another QuantEcon repo. That is how a retired repo becomes load-bearing again.
- **Two** workflows check this repo out, and both say `lfs: true` today — `.github/workflows/audit-dashboard.yml:43` (the Pages deploy) and `.github/workflows/consumed-file-check.yml:22` (every pull request). Both must become `lfs: false` while nothing published is an LFS object, and both must go back to `lfs: true` the moment anything under `lectures/` does, or Pages publishes pointer files. LFS bandwidth is an org-wide quota, so leaving them `true` once `sources/` holds a 99 MiB object spends it on every PR.

### Dynamic builders

Builders follow four stages — **fetch → pre-process → validate → write** — and only write on validation pass (expected columns/dtypes, row-count floor, recency of date range, no all-NaN columns, values unchanged in the overlap window with the previous vintage). Lectures always read the last-good snapshot: an upstream outage may fail a refresh, it must never break a lecture build.

### Live APIs

Live API calls are for *teaching data access*, not for getting data. Don't propose "the lecture should just call the API" as a fix — the fix is a snapshot here plus an automated refresh.

### Licensing and attribution

Because this repo is a **stability cache, not a content-distribution host** (see "What this repo is"), the licence question is *"is this source OK to cache and serve publicly, with attribution?"* — not *"may we republish this as our own?"*. Attribution to the upstream source is carried in every manifest (`source`: name, url, series, citation), and that is the primary obligation.

For the public data sources most snapshots come from (World Bank, FRED, Eurostat, …) the answer is a **known yes, recorded once per source** — permissive terms plus attribution. Record what the source states and move on; don't re-litigate it per snapshot. Treat the manifest's `redistribution` field as a **cheap binary gate** (`permitted` / `restricted`): a fast `permitted` for public statistics agencies, `restricted` blocking only the genuinely restricted source before it goes public — e.g. FRED re-serves third-party series that may not be redistributed, and anything under non-commercial or no-redistribution terms must not be cached here, since attribution alone does not cure those. Capture licence detail richly when the source provides it; where it is genuinely unavailable, record the gap rather than blocking the file.

**Licensing does not gate migration** (settled 2026-08-06, [#35](https://github.com/QuantEcon/data-lectures/issues/35)). A file the lectures have **already served publicly** migrates here with its licence recorded *as found* — including `redistribution: restricted` and a null licence name where that is the honest answer — and is logged in the inventory ([#35](https://github.com/QuantEcon/data-lectures/issues/35), feeding [workspace-lectures#20](https://github.com/QuantEcon/workspace-lectures/issues/20)) with a `note`. Resolve it (permission, an open replacement, or removal) before `data.quantecon.org` is promoted as a public open-data host: **that promotion is the gate, not the file's move.** Rehosting the same bytes with better provenance and an explicit licence field improves on the status quo, so a licence question is never a reason to stall a migration.

This covers **inherited** data only. A genuinely new dataset — one with no prior life in a lecture repo — still has its licence established *before* it lands, as the P5 additions all did.

### The audit dashboard stays truthful

The generated dashboard (`scripts/build_audit.py`, [#20](https://github.com/QuantEcon/data-lectures/issues/20)) verifies its three inputs against a fresh scan of the lecture repos, and the strict build **fails** when they drift. Keep them current in the same PR as the change that moves reality:

- **Landing or repointing a dataset** → update its `migration.yml` record (status, PR refs, dates). A dataset marked `repointed` whose consumers still read an old URL — or the reverse — is a build failure, by design.
- **A new manifest** (`lectures/*.yml`) → add its `migration.yml` record; delete any stale entry for the same file in `scripts/audit_annotations.yml` (manifested datasets must not be annotated there).
- **The weekly scan flags an unannotated reference** (a lecture repo started reading a new file) → classify it and add an entry to `scripts/audit_annotations.yml`; that file holds judgment (description, provenance, why-live), never facts the scan can derive.

`site/` and `audit.json` are generated — never commit them; CI rebuilds and deploys on every push to `main`.

## Cross-repo hygiene

- Changes here often pair with PRs in lecture repos and issues in `QuantEcon/meta`. In commit messages and PR bodies, **never place a GitHub closing keyword (`fixes`, `closes`, `resolves`, …) immediately before a cross-repo reference** like `QuantEcon/meta#336` — GitHub will auto-close the referenced issue when the commit lands on the default branch. Write "See QuantEcon/meta#336" or "Part of QuantEcon/meta#336".
- When a decision marked **(open)** in `PLAN.md` gets settled upstream, update `PLAN.md` and this file in the same PR that acts on it.

## Repo map

```
lectures/            # the published tree — flat, live on Pages; data.quantecon.org pending
                     #   19 datasets (10 with manifests; the 8 static intro files
                     #   and business_cycle_data.csv still need theirs) plus
                     #   business_cycle's two upstream metadata dumps (see #13)
                     #   manifests live here as sidecars: <filename>.yml
scripts/             # builders + generators — NOT published
  business_cycle.py  #   writes business_cycle_data.csv into lectures/
  build_catalog.py   #   generates CATALOG.md from the manifests
  build_audit.py     #   the audit dashboard: scan lecture repos → audit.json → site/
  render_audit.py    #   its render stage
  audit_annotations.yml  # curated judgment for not-yet-migrated data refs
migration.yml        # migration lifecycle tracker (status + PR provenance per dataset)
manifest-schema.yml  # per-dataset manifest schema (strawman)
requirements.txt
PLAN.md              # roadmap — start here
AGENTS.md            # this file
```

The Feb 2025 consumer-keyed layout (`lecture-python-intro/{static,dynamic,scripts}/`) was flattened into this tree on 2026-07-16, while nothing referenced the repo.

**That freedom is now spent — the repo is live.** The first repoint merged on 2026-07-17 (P1: `msy_fishery` in lecture-python-intro reads `lectures/lingcod_msy_recovery.csv` from `raw/main`), so every move or rename in `lectures/` is a breaking change for a live lecture build. Treat published filenames as an API: corrections in place, new vintages under new names, and check `consumers` before touching anything. Enforced by the `protect-main` ruleset (PRs only, no force-push, and the `consumed-files` check is **required** — a PR that breaks a consumed file cannot merge).
