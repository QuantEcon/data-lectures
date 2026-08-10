# `.dev/qeld/` — working artifacts behind `PLAN-QELD-PACKAGE.md`

Evidence and worklists produced while designing the `qeld` consumer-side data package. These are **inputs to
the plan, not the plan**. Where anything here disagrees with `PLAN-QELD-PACKAGE.md`, the plan wins.

Nothing here is published — the Pages job assembles `_site` from `site/`, `lectures/` and `audit.json` only.

| file | what it is |
|---|---|
| `callsites.yml` | The 115-site call-site worklist: every static data read in six lecture repos, with its idiom, the verdict against the "no more complex than fetching a url" bar, the action to take, and whether the win is structural or cosmetic. Drives the rollout ordering (`PLAN-QELD-PACKAGE.md` §7). |
| `migration-catalog.md` | The worked evidence behind the call-site rule — verbatim before/after per idiom, and the head-to-head comparison of the three candidate syntaxes. This is the spec for what a correct conversion produces. |

## Both are snapshots dated 2026-08-10

They were produced from a source sweep on that date, and **both this repo and the lecture repos moved during
the session that produced them**. The most consequential drift: the A3 `french_rev` set was repointed (#49),
so the two `.npy` files gained consumers and their conversion to CSV is no longer a free replacement.

**Regenerate the worklist before running the sweep.** Treat the catalog's examples as illustrative of the
*pattern*, and re-read the current source before converting any specific site.
