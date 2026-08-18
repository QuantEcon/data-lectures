# builders

One builder per published dataset. This directory sits **outside** the published
tree — it is never served.

## The naming rule

`builders/<stem>.<ext>` builds `lectures/<stem>.<ext2>`.

The stem is the dataset's, not the lecture's: `builders/japan_earthquakes.py`
writes `lectures/japan_earthquakes.csv`. That makes the manifest's `builder:`
field predictable and lets CI assert it.

**Where one builder produces a set of files**, name it for the set and let each
file's manifest point at the same builder path. `business_cycle.py` writes three
files; the SCF and Forbes builders each write two. The rule is the default, not
an invariant — what CI asserts is that every `builder:` path exists, and that a
dataset claiming a builder names one.

## The contract

Builders follow four stages — **fetch → pre-process → validate → write** — and
only write on validation pass. Lectures always read the last-good snapshot: an
upstream outage may fail a refresh, it must never break a lecture build. The
template and the architecture discussion are in
[#14](https://github.com/QuantEcon/data-lectures/issues/14).

Most builders fetch from the third-party upstream at run time, which is the
normal case. A builder reads from `sources/` only when its input **cannot be
re-fetched** — see `AGENTS.md`.

## What is here

| Builder | Writes to `lectures/` | Status |
| --- | --- | --- |
| `ames_house_prices.py` | `ames_house_prices.csv` | committed |
| `epl_match_goals.py` | `epl_match_goals.csv` | committed |
| `japan_deaths_by_age.py` | `japan_deaths_by_age.csv` | committed |
| `japan_earthquakes.py` | `japan_earthquakes.csv` | committed |
| `japan_population_by_age.py` | `japan_population_by_age.csv` | committed |
| `us_adult_heights.py` | `us_adult_heights.csv` | committed |
| `NEWQDATA.py` | `NEWQDATA.csv` | committed — reads a committed input (`sources/NEWQDATA.MAT`) instead of fetching. Its upstream is published nowhere; see `sources/README.md`. Reproduces its output byte for byte |
| `dataBHS.py` | `dataBHS.csv` | committed — the second `sources/` reader (`sources/dataBHS.mat`, un-refetchable; see `sources/README.md`). A value-preserving MATLAB-to-CSV conversion; validates the consuming lecture's hardcoded moments on every run |
| `bbh_macro_quarterly.py` | `bbh_macro_quarterly.csv` | committed — range-reads one workbook out of the 198.8 MB Zenodo replication package. Reproduces its output byte for byte (2026-08-17) |
| `bbh_michigan_monthly.py` | `bbh_michigan_monthly.csv` | committed — same Zenodo package, different workbook. Reproduces its output byte for byte (2026-08-17) |
| `fred_data.py` | `fred_data.csv` | committed — fetches six FRED series live over a pinned 1953-04..2024-12 window (yields and the recession dummy are stable history, unlike the BBH national-accounts snapshot). Reproduces its output byte for byte (2026-08-18) |
| `hansen_singleton_1982_data.py` | `hansen_singleton_1982_data.csv` | committed — fetches FRED and the Ken French factors live. Reproduces its output byte for byte (2026-08-13) |
| `hansen_singleton_1983_data.py` | `hansen_singleton_1983_data.csv` | committed — the same construction plus a T-bill leg, so its output is a strict superset of the 1982 file's. Reproduces its output byte for byte (2026-08-13) |
| `business_cycle.py` | `business_cycle_data.csv`, `business_cycle_info.md`, `business_cycle_metadata.md` | run by hand, no validate stage yet (PLAN Phase 5); its three outputs are the repo's only unmanifested files |
| `webscrape_forbes.ipynb` | `forbes-global2000.csv`, `forbes-billionaires.csv` | **committed-frozen** — an undocumented Forbes API, a spoofed user-agent and hardcoded GDPR consent cookies. Defects recorded in the two manifests rather than fixed |
| `generating_mini.md` | `SCF_plus_mini.csv`, `SCF_plus_mini_no_weights.csv` | **committed-frozen** — its `to_csv` calls are commented out upstream and stay that way. As written it still fetches the `high_dim_data` URL; that URL is historical, and the input is now committed at `sources/SCF_plus.dta`. See `sources/README.md` |
| `usa-gini-nwealth-tincome-lincome.ipynb` | `usa-gini-nwealth-tincome-lincome.csv` | **committed-frozen** — three independent reasons, any one sufficient: no validate stage; it raises under the pinned pandas 3 (`np.asarray` of a Series is read-only under copy-on-write, so `rd.shuffle` fails — the lecture got the `.copy()` fix in QuantEcon/lecture-python-intro#776, this notebook did not); and it is non-deterministic, so it cannot reproduce its own bytes. It is also the only builder here whose input is **another file in this repo** |

The two `high_dim_data` builders keep their upstream filenames rather than being
renamed to their set stems (`forbes`, `SCF_plus_mini`), which preserves the
textual link to that repo's history. Permitted by the rule above — what CI
asserts is that the path exists. `usa-gini-nwealth-tincome-lincome.ipynb` takes
the opposite choice deliberately: its upstream name was `data.ipynb`, which is
meaningless in a flat directory, so it is renamed to its output stem.

The two `hansen_singleton_*` builders are the case that leaves no choice at all.
Both were called `make_data.py`, sitting beside their own output in separate
`_static/lecture_specific/<lecture>/` directories where the parent directory
supplied the meaning. Flattened into one tree they collide outright, so each
takes its dataset's stem — the rule's default, arrived at by necessity rather
than by preference.

**A frozen builder is committed verbatim and not edited.** That is what makes it
provenance rather than code, and it is why the pandas-3 defect above is recorded
here instead of patched — fixing it would mean this file is no longer the thing
that produced those bytes. The fix belongs in `lecture-python-intro`, which still
serves that notebook to readers.

**This listing is the coverage report.** The repo has 28 `constructed` datasets
(re-derived from the parsed manifests, 2026-08-18). Eighteen ship a builder (13
`committed`, 5 `committed-frozen`), carried by **16** distinct builder files —
fewer than the datasets because `generating_mini.md` and
`webscrape_forbes.ipynb` each produce two. The remaining **10** have none: they
carry `builder_status: unrecovered` in their manifests, which is the Phase 9
recovery backlog, kept visible rather than hidden by reclassifying the file as
`verbatim`. The table above lists a **17th** builder, `business_cycle.py`, which
no manifest references — its three outputs are the repo's only unmanifested
files.

Repo tooling — the audit dashboard and the catalog generator — lives in
`scripts/` and is not a builder.
