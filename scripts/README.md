# scripts

Repo tooling. This directory sits **outside** the published tree — it is never
served, and nothing here produces a dataset.

Dataset builders live in [`builders/`](../builders/), one per published file.

| Script | What |
| --- | --- |
| `build_audit.py` | the audit dashboard: scans the 8 lecture repos, writes `audit.json`, renders `site/`. `--strict` fails on an unannotated data reference, on migration-status drift, and on a repoint that names a host, ref or path this repo does not serve |
| `render_audit.py` | the render stage of `build_audit.py` (HTML generation) |
| `build_catalog.py` | generates `CATALOG.md` from the manifests (`lectures/*.yml`) |
| `audit_annotations.yml` | curated judgment for not-yet-migrated data references — the strict scan fails when a new reference has no entry here and no manifest |
