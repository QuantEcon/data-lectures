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
| `NEWQDATA.py` | `NEWQDATA.csv` | committed — the **only** builder here that reads a committed input (`sources/NEWQDATA.MAT`) instead of fetching. Its upstream is published nowhere; see `sources/README.md`. Reproduces its output byte for byte |
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

**A frozen builder is committed verbatim and not edited.** That is what makes it
provenance rather than code, and it is why the pandas-3 defect above is recorded
here instead of patched — fixing it would mean this file is no longer the thing
that produced those bytes. The fix belongs in `lecture-python-intro`, which still
serves that notebook to readers.

**This listing is the coverage report.** The repo has 18 `constructed` datasets
and 10 builders; the difference is the Phase 9 recovery backlog, carried as
`builder_status: unrecovered` in each manifest rather than hidden by
reclassifying the file as `verbatim`.

Repo tooling — the audit dashboard and the catalog generator — lives in
`scripts/` and is not a builder.
