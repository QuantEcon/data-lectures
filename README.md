# data-lectures

The canonical repository for **data consumed by the QuantEcon lecture series**, referenced by stable URLs.

> **Status:** renamed from `QuantEcon/data` (2026-07-16) and being shaped into the canonical lecture-data repo per [QuantEcon/meta#336](https://github.com/QuantEcon/meta/issues/336). See [`PLAN.md`](PLAN.md) for the roadmap and [`AGENTS.md`](AGENTS.md) for working conventions. The full data-hosting convention is drafted in [QuantEcon.manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108).

## The routing rule

- Data consumed by lectures → **this repo**, referenced by a stable URL
- Data owned by a specific book, project, or package → that project's own repo
- Never commit a new dataset into a lecture repository

## Referencing data

Until the `data.quantecon.org` Pages deployment is live, use the interim form — it works for both plain-git and LFS-tracked files:

```
https://github.com/QuantEcon/data-lectures/raw/main/<path>
```

Once publishing lands (PLAN Phase 4), the canonical form becomes:

```
https://data.quantecon.org/lectures/<filename>
```

Avoid `raw.githubusercontent.com` (serves pointer text for LFS-tracked files), `media.githubusercontent.com` (404s for plain-git files), and any URL pinning a non-default branch.

## Adding a dataset

1. Confirm the license permits redistribution.
2. Classify it: **verbatim** (third-party file as distributed), **constructed** (built by our processing — commit the builder too), or **dynamic snapshot** (tracks a moving source — builder plus refresh cadence).
3. Open a PR with the file, its manifest, and any builder.
4. Reference it from the lecture by the canonical URL — the lecture PR builds green immediately, no two-step merge.
5. Add the lecture to the dataset's `consumers` list.

See the [draft convention](https://github.com/QuantEcon/QuantEcon.manual/pull/108) for the full checklist and manifest schema.

## Layout

| Path | What | Published |
| --- | --- | --- |
| `lectures/` | the published tree — flat. Every dataset lives here, directly. No folder implies ownership by a lecture series: any lecture may consume any file | yes |
| `scripts/` | builders for constructed and dynamic datasets, plus the audit-dashboard generator | no |
| `manifest-schema.yml` | the per-dataset manifest schema (strawman — see [`PLAN.md`](PLAN.md) Phase 2) | no |
| `migration.yml` | the migration lifecycle tracker — which PRs landed and repointed each dataset (transitional; archivable when the migration programme completes) | rendered |

The tree is flat because the URL is the interface: `lectures/<filename>` maps to
`data.quantecon.org/lectures/<filename>`, so a file can never be re-filed under a
new owner and break its consumers. Anything outside `lectures/` is not served.

## The audit dashboard

A **generated** dashboard covering all data referenced by the 8 synced
Python-family lecture repos — the full-universe audit plus a per-dataset
migration tracker — deploys to this repo's GitHub Pages site alongside the
published `lectures/` tree ([data-lectures#20](https://github.com/QuantEcon/data-lectures/issues/20)).

```
python scripts/build_audit.py all --strict     # scan + render into site/
```

The scan greps each lecture repo's `main` (clones under `--repos-dir`; defaults
to this repo's parent, matching the workspace-lectures layout), classifies every
data reference, and reconciles three sources of truth: the manifests
(`lectures/*.yml`, migrated datasets), `migration.yml` (lifecycle + PR
provenance), and `scripts/audit_annotations.yml` (curated judgment for
not-yet-migrated references). A new data reference with no annotation, or a
migration status the scan contradicts, **fails the build** — the dashboard
cannot silently rot. CI rebuilds it on push to `main`, weekly, and on demand
(`.github/workflows/audit-dashboard.yml`).
