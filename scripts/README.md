# scripts

Builders for the datasets in `lectures/`. This directory sits **outside** the
published tree — it is never served.

Every **constructed** and **dynamic snapshot** dataset must ship its builder
here (see `AGENTS.md`). A constructed dataset without a committed builder is a
bug.

| Builder | Writes to `lectures/` |
| --- | --- |
| `business_cycle.py` | `business_cycle_data.csv`, `business_cycle_info.md`, `business_cycle_metadata.md` |

`business_cycle.py` is run by hand today and has no validate stage; retrofitting
it to the four-stage contract (fetch → pre-process → validate → write) is
PLAN Phase 5.
