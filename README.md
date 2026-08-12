# data-lectures

The canonical repository for **data consumed by the QuantEcon lecture series**, referenced by stable URLs.

> **Status:** renamed from `QuantEcon/data` (2026-07-16) and being shaped into the canonical lecture-data repo per [QuantEcon/meta#336](https://github.com/QuantEcon/meta/issues/336). See [`PLAN.md`](PLAN.md) for the roadmap and [`AGENTS.md`](AGENTS.md) for working conventions. The full data-hosting convention is drafted in [QuantEcon.manual#108](https://github.com/QuantEcon/QuantEcon.manual/pull/108).

## The routing rule

- Data consumed by lectures → **this repo**, referenced by a stable URL
- Data owned by a specific book, project, or package → that project's own repo
- Never commit a new dataset into a lecture repository

## Referencing data

The stable consumer interface is the **`qeld` package** ([`PLAN-QELD-PACKAGE.md`](PLAN-QELD-PACKAGE.md) — designed, not yet shipped): lecture code reads `qeld.url('<filename>')` in place of a URL literal, which resolves to the context-correct direct form below and keeps the URL one `print(url)` away. There is no pending host cutover — the `data.quantecon.org` custom domain was **deferred indefinitely on 2026-08-12** in favor of `qeld` (D11, [#37](https://github.com/QuantEcon/data-lectures/issues/37)), so the direct forms below are standing, not interim.

Until `qeld` ships (and permanently for prose links, `{download}` targets, and reads whose URL is the lesson), use the direct form. **There is no single safe form — it depends on the consumer's runtime** (repoint rule 5):

| Consumer | Use |
| --- | --- |
| CPython — site notebooks, Colab, every series except `lecture-wasm` | `https://github.com/QuantEcon/data-lectures/raw/main/lectures/<file>` |
| Browser — `lecture-wasm` code cells, which execute under Pyodide in the reader's browser | `https://raw.githubusercontent.com/QuantEcon/data-lectures/main/lectures/<file>` |

The `github.com/…/raw/` form is a 302 whose response carries an **empty** `access-control-allow-origin`, so a browser rejects it before following the redirect. The strict audit fails on any `lecture-wasm` code-cell read that uses it. `{download}` targets and prose links are plain navigations, so any resolving form is fine there.

**Never** use `media.githubusercontent.com`. It is the LFS media endpoint and routes per path, so it 404s every file this repo publishes — `lectures/` is 100% plain git, and LFS is confined to `sources/`, which is never served ([#58](https://github.com/QuantEcon/data-lectures/issues/58)). Never pin a branch other than `main`.

## Adding a dataset

1. Confirm the license permits redistribution.
2. Classify it: **verbatim** (third-party file as distributed), **constructed** (built by our processing — commit the builder too), or **dynamic snapshot** (tracks a moving source — builder plus refresh cadence).
3. Open a PR with the file, its manifest, and any builder.
4. Reference it from the lecture — `qeld.url('<filename>')` once the package ships, the runtime-correct direct URL until then. The lecture PR builds green immediately, no two-step merge.
5. Add the lecture to the dataset's `consumers` list.

See the [draft convention](https://github.com/QuantEcon/QuantEcon.manual/pull/108) for the full checklist and manifest schema.

## Layout

| Path | What | Published |
| --- | --- | --- |
| `lectures/` | the published tree — flat. Every dataset lives here, directly. No folder implies ownership by a lecture series: any lecture may consume any file | yes |
| `scripts/` | builders for constructed and dynamic datasets, plus the audit-dashboard generator | no |
| `manifest-schema.yml` | the per-dataset manifest schema (strawman — see [`PLAN.md`](PLAN.md) Phase 2) | no |
| `migration.yml` | the migration lifecycle tracker — which PRs landed and repointed each dataset (transitional; archivable when the migration programme completes) | rendered |

The tree is flat because the filename is the interface: `lectures/<filename>` is
the served URL's last segment and the `qeld` key (`qeld.url('<filename>')`), so a
file can never be re-filed under a new owner and break its consumers. Anything
outside `lectures/` is not served.

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
