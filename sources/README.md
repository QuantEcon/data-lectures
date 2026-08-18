# sources

Inputs that a builder consumes and **no lecture reads**. This directory sits
outside the published tree — it is never served, and nothing here has a sidecar
manifest. This file is the audit trail instead: origin, retrieval, licence,
upstream identifier, `sha256`, and the builder that consumes each entry.

## What belongs here — and what does not

The defining property is **un-refetchability**, not size.

The normal case for a builder is to fetch from its third-party upstream at run
time, and that is what most of them do: `jse.amstat.org`, `earthquake.usgs.gov`,
`wwwn.cdc.gov`, `stat.go.jp`, `openfootball`, `fred.stlouisfed.org`,
`mba.tuck.dartmouth.edu`. **Eight of the nine `committed`
builders in this repo fetch at run time and have no committed input**; the
exception is `NEWQDATA.py`, whose upstream is not published anywhere. So
`sources/` is not "where builder inputs live" as a general rule — it is the
exception layer for an input that cannot be obtained again.

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

---

## `NEWQDATA.MAT`

| | |
| --- | --- |
| **Origin** | Cogley and Sargent's own MATLAB replication directory for "Drifts and Volatilities". Located in 2026 only as a third-party GitHub mirror (`szokeb87/cs2005_pymc`, `matlab_files_from_cogley/`), whose README states the MATLAB files "were written entirely by Tim Cogley and Thomas Sargent" |
| **Upstream** | Cogley, Timothy, and Thomas J. Sargent (2005), *Drifts and Volatilities: Monetary Policies and Outcomes in the Post WWII U.S.*, Review of Economic Dynamics 8(2), 262-302 |
| **Upstream identifier** | DOI [10.1016/j.red.2004.10.009](https://doi.org/10.1016/j.red.2004.10.009) — the **article**. There is no dataset DOI; Crossref registers no dataset component |
| **Retrieved** | `null` — no retrieval date was recorded upstream, and the mirror's commit dates record when a third party acquired the file, not when it came from the authors. Do not promote one to the other |
| **Licence** | `null` — no licence statement exists at the journal, the authors' pages, or the mirror. Registered on [#35](https://github.com/QuantEcon/data-lectures/issues/35) |
| **`sha256`** | `ab760926f37b41e7478c5227454f3d5c142acb4ad27428f0881ad5140dcb8162` |
| **Size** | 7,104 B |
| **Consumed by** | `builders/NEWQDATA.py` (`builder_status: committed`) |
| **Produces** | `lectures/NEWQDATA.csv` |

### Why this file is here rather than fetched at run time

This is the repo's **first committed input to a builder that actually runs**,
so the exception deserves its reasoning in full.

The file is un-refetchable from any authoritative source. Searched to
exhaustion on 2026-08-13:

- **tomsargent.com** and Cogley's NYU pages — live and via the Wayback Machine
  — carry no replication files for this paper;
- the **Review of Economic Dynamics / SED** site publishes no data archive, and
  had no data-availability policy in 2005;
- **RePEc**'s record for the article lists no dataset;
- **ScienceDirect** returns 403 to an anonymous fetch;
- **Crossref** registers no dataset component, only Elsevier text-mining
  licences for the article text.

The single copy located anywhere was the third-party mirror above. A builder
that fetches from a stranger's repository at run time is precisely the
fragility this directory exists to remove — the same failure shape as a network
read from a retired QuantEcon repo, with less recourse. So the input is
committed here, and `builders/NEWQDATA.py` reads it from disk.

The conversion is value-preserving — four arrays to four columns, no filtering,
no rescaling, no reordering — and the builder reproduces
`lectures/NEWQDATA.csv` **byte for byte**, all 13,738 of them. That is what
earns the manifest's `integrity.upstream.status: verified` under AGENTS.md's
definition for a `constructed` dataset ("re-run the builder and compare"),
rather than by analogy to a verbatim re-fetch.

### Size

7,104 B — four orders of magnitude below any limit that matters. It is here on
the un-refetchability test alone, which is the test, and a useful counterweight
to reading this directory as "the big-file directory".

---

## `dataBHS.mat`

| | |
| --- | --- |
| **Origin** | The authors' MATLAB data file for "Doubts or variability?", inherited as `lectures/dataBHS.mat` in `QuantEcon/lecture-python-advanced.myst` (where it sat at the lectures root, outside `html_static_path`, and was never served by the published site). Byte-identical copies exist in `lecture-tools-techniques` (which reads its own), `python-lecture-sandpit.myst` and `lecture-mapping` — all QuantEcon-internal descendants of the same inheritance, not an upstream |
| **Upstream** | Barillas, Francisco, Lars Peter Hansen, and Thomas J. Sargent (2009), *Doubts or variability?*, Journal of Economic Theory 144(6), 2388-2418 |
| **Upstream identifier** | DOI [10.1016/j.jet.2008.11.014](https://doi.org/10.1016/j.jet.2008.11.014) — the **article**. The JET article carries no data supplement |
| **Retrieved** | `null` — no retrieval date was recorded upstream; the lecture-repo commit dates record when QuantEcon acquired it, not when it came from the authors. Do not promote one to the other |
| **Licence** | `null` — no licence statement exists at the journal or the authors' pages. Registered on [#35](https://github.com/QuantEcon/data-lectures/issues/35) |
| **`sha256`** | `28c5f85286718e70b205f6a3fb269ebb49bd635194e2d0d488409b017be5e890` |
| **Size** | 5,588 B |
| **Consumed by** | `builders/dataBHS.py` (`builder_status: committed`) |
| **Produces** | `lectures/dataBHS.csv` |

### Why this file is here rather than fetched at run time

Un-refetchable from any authoritative source, on the NEWQDATA precedent.
Searched 2026-08-18, each zero beside a passing control:

- **tomsargent.com**'s source-code page returns 404 (and the site's https
  endpoint does not answer);
- **larspeterhansen.org** hosts the paper's PDF but lists no code or data for
  it on the research pages;
- the **Journal of Economic Theory** article (ScienceDirect) shows no
  supplementary material;
- a **GitHub-wide code search** for `dataBHS` returns only QuantEcon's own
  inherited copies of this blob (plus token-collision noise in unrelated
  JavaScript), with the same search finding `NEWQDATA` in five QuantEcon
  files as the positive control.

Unlike NEWQDATA there is not even a third-party mirror of an authors'
directory — every locatable copy descends from the QuantEcon inheritance. So
the input is committed here, and `builders/dataBHS.py` reads it from disk.

The file is MATLAB 5.0 (PCWIN, created 2007-05-11) holding exactly three
(236,1) float64 arrays `c`, `rb`, `rs` — 1948Q1-2006Q4, the paper's sample.
The conversion is value-preserving (three arrays to three columns, no
filtering, no rescaling, no reordering); the CSV parses back **bit-exactly**
under `float_precision='round_trip'`, and the consuming lecture's histogram is
identical under pandas' default parser (PLAN-QELD-PACKAGE.md §4.3 measured why
those are different claims). That is what earns the manifest's
`integrity.upstream.status: verified` under AGENTS.md's definition for a
`constructed` dataset.

### Size

5,588 B — here on the un-refetchability test alone, like NEWQDATA above.
