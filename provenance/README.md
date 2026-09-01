# provenance

Upstream metadata dumps that a builder writes **alongside** its dataset but
that are not datasets themselves. Nothing here is served: the Pages job
assembles `_site` from `site/`, `lectures/` and `audit.json` only, and no
lecture reads a file from this directory.

The distinction this directory exists to keep is between a **published
dataset** (`lectures/<file>`, with a sidecar manifest, a class, a licence and
a filename that is an API) and a **provenance byproduct** — the raw record of
what the upstream said about itself on the day a builder ran. The two
`business_cycle` dumps below lived in `lectures/` from the 2026-07-16 flatten
until they were moved here (QuantEcon/data-lectures#13): served at public
URLs, indistinguishable from datasets to anyone browsing the tree, and
failing every rule a dataset must meet.

| File | Written by | What it is |
| --- | --- | --- |
| `business_cycle_metadata.md` | `builders/business_cycle.py` | `wb.series.metadata.get('NY.GDP.MKTP.KD.ZG')` — the World Bank's own record for the series: definition, source, periodicity and the `License_Type: CC BY-4.0` / `License_URL` fields that `lectures/business_cycle_data.csv.yml` cites |
| `business_cycle_info.md` | `builders/business_cycle.py` | `wb.series.info(q='GDP growth')` — the fuzzy-search listing the consuming lecture teaches; kept because the builder reproduces the lecture's own query, not because anything reads it |

Files here carry no manifest and no hash gate. Runs of blank lines in the
upstream text are collapsed to one before writing — whitespace carries no
evidence, and the raw World Bank dump had runs ten newlines deep. They are
**regenerated on every builder run** and are expected to drift: between the committed dump of
2025-02 and a run on 2026-09-01 the World Bank rewrote the metadata prose and
added a `Dataset: WB_WDI` line. The manifest's typed `source` and `license`
fields are the durable record; a dump is the evidence they were read from.
