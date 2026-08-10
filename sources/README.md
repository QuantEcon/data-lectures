# sources

Inputs that a builder consumes and **no lecture reads**. This directory sits
outside the published tree — it is never served, and nothing here has a sidecar
manifest. This file is the audit trail instead: origin, retrieval, licence,
upstream identifier, `sha256`, and the builder that consumes each entry.

## What belongs here — and what does not

The defining property is **un-refetchability**, not size.

The normal case for a builder is to fetch from its third-party upstream at run
time, and that is what most of them do: `jse.amstat.org`, `earthquake.usgs.gov`,
`wwwn.cdc.gov`, `stat.go.jp`, `openfootball`. **None of the six `committed`
builders in this repo has a committed input.** So `sources/` is not "where
builder inputs live" as a general rule — it is the exception layer for an input
that cannot be obtained again.

It is also emphatically **not "the big-file directory"**, even though
`.gitattributes` LFS-tracks everything under it. A 300 MB file that can be
re-fetched from a stable upstream does not belong here; a 4 KB file whose source
has vanished does.

What it must never hold is a network read from another QuantEcon repo. That is
how a retired repo becomes load-bearing again.

## LFS, and why this directory has it

`sources/**` is LFS-tracked and `lectures/` is not — deliberately, and in that
direction only ([#58](https://github.com/QuantEcon/data-lectures/issues/58)).
The published tree is 100% plain git because an LFS-tracked path returns **HTTP
200 with ~130 bytes of pointer text** from `raw.githubusercontent.com`: a reader
gets a parse error rather than a 404, `pd.read_csv` raises nothing, and a
status-code check reads as green. Nothing here is served, so nothing here can
meet that trap.

`README.md` is excluded from the LFS rule so this audit trail stays readable
text on GitHub.

**Before `git add`ing anything to this directory**, confirm the rule actually
captures it:

    git check-attr filter -- sources/<file>      # must print: filter: lfs

That is a real gate, not a formality — see the size note under `SCF_plus.dta`.

---

## `SCF_plus.dta`

| | |
| --- | --- |
| **Origin** | Inherited from `QuantEcon/high_dim_data` (`SCF_plus/SCF_plus.dta`), where it was LFS-tracked. Folded in 2026-08-10 when that repo was retired |
| **Upstream** | SCF+ — Kuhn, Schularick and Steins (2020), *Income and Wealth Inequality in America, 1949-2016*, Journal of Political Economy 128(9), 3469-3519 |
| **Upstream identifier** | DOI [10.1086/708815](https://doi.org/10.1086/708815) — the **article**. No data deposit was locatable; see "Provenance gap" below |
| **Retrieved** | `null` — no retrieval date was recorded upstream, and the per-file commit dates in `high_dim_data` record when QuantEcon acquired it, not when it was obtained from the source. Do not promote one to the other |
| **Licence** | `null` — no licence statement was locatable at any deposit. Registered on [#35](https://github.com/QuantEcon/data-lectures/issues/35) |
| **`sha256`** | `c208ccd49b3bd11205a88bce08864ea445898b182098002fd6b5e38664aa3f01` |
| **Size** | 103,934,093 B |
| **Consumed by** | `builders/generating_mini.md` (`builder_status: committed-frozen`) |
| **Produces** | `lectures/SCF_plus_mini.csv`, `lectures/SCF_plus_mini_no_weights.csv` |

### The size note — this file must stay LFS-tracked permanently

103,934,093 B against GitHub's hard blob limit of 104,857,600 B leaves
**923,507 B of headroom — 0.88%**.

That margin is what makes the `check-attr` gate above load-bearing rather than
ceremonial. A mis-scoped LFS rule does **not** error on a file this size: the
push simply succeeds as plain git, and a 99 MiB blob is in the repository's
history permanently, with no way to remove it short of a history rewrite. The
failure is silent in exactly the direction that cannot be undone.

An upstream vintage 1% larger could not be pushed as plain git at all.

### Provenance gap

The SCF+ deposit record could not be located, and this was searched to
exhaustion on 2026-08-10 rather than assumed:

- Crossref registers `10.1086/708815` with `license: null` and **no data
  relation**;
- DataCite returns zero results;
- Harvard Dataverse returns zero results;
- openICPSR and the JPE supplementary-material path both return **403**.

So `retrieved` and `license` above are honest nulls with this note, not
placeholders awaiting a lookup someone else should repeat. If a deposit is
located later, both fields and the two manifests' `integrity.upstream` blocks
can be filled in together.

The variable dictionary inherited as `SCF_plus/README.md` upstream is **not**
provenance: it carries no URL, no date, no licence and no DOI. Its content was
migrated into `lectures/SCF_plus_mini.csv.yml`'s `schema.columns[].description`
rather than landing here as a second, unstructured record beside the structured
one.

### The builder reads a URL, not this file — and that is deliberate

`builders/generating_mini.md` still contains:

    pd.read_stata('https://github.com/QuantEcon/high_dim_data/blob/main/SCF_plus/SCF_plus.dta?raw=true')

That URL is **historical, not a live dependency.** The builder is
`committed-frozen`: it is kept as the record of what produced the two published
extracts and deliberately will not run, so it is committed verbatim and not
edited — editing it is what would destroy its value as provenance
([#14](https://github.com/QuantEcon/data-lectures/issues/14),
[#61](https://github.com/QuantEcon/data-lectures/pull/61)).

The rule requiring a builder to read its input from `sources/` binds builders
that **run**. This is the substitution recorded as prose, which is where a
frozen builder's corrections belong: **the input is now committed at
`sources/SCF_plus.dta`, byte-identical to what that URL served.**

`high_dim_data` is archived rather than deleted, so the URL above continues to
resolve. Do not treat that as a reason to leave the dependency live in any
builder that does run — and do not delete branches or rewrite history on that
repo after archiving, which is what actually breaks an external reader.
