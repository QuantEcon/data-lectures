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

## Current contents

| Path | What |
| --- | --- |
| `lecture-python-intro/static/` | 10 static files migrated from `lecture-python-intro` (Feb 2025) — legacy consumer-keyed layout, restructure pending |
| `lecture-python-intro/dynamic/` | `business_cycle_data.csv`, the one dynamic snapshot |
| `lecture-python-intro/scripts/` | `business_cycle.py`, its builder (manual refresh for now) |
