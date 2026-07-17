<!-- GENERATED FILE — do not edit by hand. -->
<!-- Regenerate: python scripts/build_catalog.py -->
<!-- Source of truth: the per-dataset manifests at lectures/<file>.yml -->

# Dataset catalog — `QuantEcon/data-lectures`

The migrated-dataset registry, **auto-generated** from the sidecar manifests (`lectures/*.yml`). Do not edit by hand — run `python scripts/build_catalog.py`. A dataset appears here once it has a manifest; files not yet migrated are tracked in [PLAN.md](PLAN.md) Phase 9.

**4 datasets migrated** · 1.8 MB total · 3 permitted / 1 restricted redistribution

| Dataset | Class | Source | Licence | Redist. | Integrity | Builder | Size | Used by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [**countries.csv**](https://github.com/QuantEcon/data-lectures/raw/main/lectures/countries.csv)<br><sub>WorldData.info country reference table</sub> | verbatim | [WorldData.info — country data downloads](https://www.worlddata.info/downloads/) | Proprietary — © WorldData.info, all rights reserved | ⚠️ restricted | ⚠️ unverifiable | n/a (verbatim) | 48.4 KB | [lecture-python-programming · pandas_panel.md](https://github.com/QuantEcon/lecture-python-programming/blob/main/lectures/pandas_panel.md)<br>[lecture-python.myst · pandas_panel.md](https://github.com/QuantEcon/lecture-python.myst/blob/main/lectures/pandas_panel.md) |
| [**employ.csv**](https://github.com/QuantEcon/data-lectures/raw/main/lectures/employ.csv)<br><sub>Eurostat employment in Europe — by age and sex, 2007–2016</sub> | constructed | [Eurostat — Employment database](https://ec.europa.eu/eurostat/data/database) | Eurostat reuse (Commission Decision 2011/833/EU) | ✅ permitted | ⚠️ unverifiable | ⚠️ unrecovered | 1.6 MB | [lecture-python-programming · pandas_panel.md](https://github.com/QuantEcon/lecture-python-programming/blob/main/lectures/pandas_panel.md)<br>[lecture-python.myst · pandas_panel.md](https://github.com/QuantEcon/lecture-python.myst/blob/main/lectures/pandas_panel.md) |
| [**lingcod_msy_recovery.csv**](https://github.com/QuantEcon/data-lectures/raw/main/lectures/lingcod_msy_recovery.csv)<br><sub>Pacific Coast lingcod — biomass and fishing pressure relative to MSY</sub> | constructed | [RAM Legacy Stock Assessment Database](https://www.ramlegacy.org/) | CC BY 4.0 | ✅ permitted | ⚠️ unverifiable | ⚠️ unrecovered | 2.3 KB | [lecture-python-intro · msy_fishery.md](https://github.com/QuantEcon/lecture-python-intro/blob/main/lectures/msy_fishery.md) |
| [**realwage.csv**](https://github.com/QuantEcon/data-lectures/raw/main/lectures/realwage.csv)<br><sub>OECD real minimum wages — 32 countries, 2006–2016</sub> | constructed | [OECD — Real minimum wages (RMW)](https://stats.oecd.org/Index.aspx?DataSetCode=RMW) | CC BY 4.0 | ✅ permitted | ⚠️ unverifiable | ⚠️ unrecovered | 118.7 KB | [lecture-python-programming · pandas_panel.md](https://github.com/QuantEcon/lecture-python-programming/blob/main/lectures/pandas_panel.md)<br>[lecture-python.myst · pandas_panel.md](https://github.com/QuantEcon/lecture-python.myst/blob/main/lectures/pandas_panel.md) |

---

**Legend** — *Integrity* is the `integrity.upstream.status` (is this what the source says?): ✅ verified · ◑ spot-checked · ⚠️ unverifiable · … unverified · ❌ failing. *Redist.* ⚠️ restricted files are cached as inherited exposures and tracked for licence review ([workspace-lectures#20](https://github.com/QuantEcon/workspace-lectures/issues/20)). *Builder* ⚠️ unrecovered marks a constructed dataset whose builder was never committed (PLAN Phase 9).
