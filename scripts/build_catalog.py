#!/usr/bin/env python3
"""Generate CATALOG.md — the migrated-dataset registry — from the sidecar
manifests in lectures/*.yml.

CATALOG.md is a GENERATED file: the per-dataset manifests are the source of
truth, and this script is the only thing that should write the catalog. Run it
after adding or editing any manifest:

    python scripts/build_catalog.py

CI asserts the catalog is current with `git diff --exit-code CATALOG.md` after
regenerating, so a stale catalog fails the build (PLAN Phase 5).

Scope: migrated-only. A dataset appears here once it has a manifest; files in
lectures/ without a manifest are not yet migrated and are tracked in PLAN
Phase 9, not here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
LECTURES = REPO / "lectures"
OUT = REPO / "CATALOG.md"

# Interim URL form (AGENTS.md); swaps to data.quantecon.org/lectures/ at Phase 4.
RAW = "https://github.com/QuantEcon/data-lectures/raw/main/lectures"


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def oneline(text) -> str:
    """Collapse a folded/multiline scalar to a single trimmed line."""
    if text is None:
        return ""
    return " ".join(str(text).split())


def load_manifests():
    manifests = []
    for path in sorted(LECTURES.glob("*.yml")):
        with path.open(encoding="utf-8") as f:
            m = yaml.safe_load(f)
        if not isinstance(m, dict) or "filename" not in m:
            print(f"skip (not a manifest): {path.name}", file=sys.stderr)
            continue
        m["_manifest_path"] = path
        data_file = LECTURES / m["filename"]
        m["_size"] = data_file.stat().st_size if data_file.exists() else None
        manifests.append(m)
    return manifests


def fmt_consumers(consumers) -> str:
    if not consumers:
        return "—"
    parts = []
    for c in consumers:
        repo = c.get("repo", "")
        short = repo.split("/")[-1] if repo else "?"
        file = c.get("file", "")
        stem = file.split("/")[-1] if file else ""
        if repo and file:
            parts.append(f"[{short} · {stem}](https://github.com/{repo}/blob/main/{file})")
        else:
            parts.append(f"{short} · {stem}".strip(" ·"))
    return "<br>".join(parts)


def fmt_source(source) -> str:
    if not isinstance(source, dict):
        return oneline(source)
    name = oneline(source.get("name", ""))
    url = source.get("url")
    return f"[{name}]({url})" if url else name


def fmt_redist(license) -> str:
    if not isinstance(license, dict):
        return "?"
    r = license.get("redistribution", "?")
    return {"permitted": "✅ permitted", "restricted": "⚠️ restricted"}.get(r, str(r))


def fmt_integrity(integrity) -> str:
    if not isinstance(integrity, dict):
        return "?"
    up = integrity.get("upstream") or {}
    status = up.get("status", "?")
    mark = {"verified": "✅", "spot-checked": "◑", "unverifiable": "⚠️",
            "unverified": "…", "failing": "❌"}.get(status, "")
    return f"{mark} {status}".strip()


def fmt_builder(m) -> str:
    if m.get("class") == "verbatim":
        return "n/a (verbatim)"
    bs = m.get("builder_status", "?")
    return {"committed": "✅ committed", "unrecovered": "⚠️ unrecovered",
            "not-applicable": "n/a"}.get(bs, str(bs))


def build(manifests) -> str:
    total = sum(m["_size"] or 0 for m in manifests)
    permitted = sum(1 for m in manifests
                    if (m.get("license") or {}).get("redistribution") == "permitted")
    restricted = len(manifests) - permitted

    lines = []
    lines.append("<!-- GENERATED FILE — do not edit by hand. -->")
    lines.append("<!-- Regenerate: python scripts/build_catalog.py -->")
    lines.append("<!-- Source of truth: the per-dataset manifests at lectures/<file>.yml -->")
    lines.append("")
    lines.append("# Dataset catalog — `QuantEcon/data-lectures`")
    lines.append("")
    lines.append(
        "The migrated-dataset registry, **auto-generated** from the sidecar "
        "manifests (`lectures/*.yml`). Do not edit by hand — run "
        "`python scripts/build_catalog.py`. A dataset appears here once it has a "
        "manifest; files not yet migrated are tracked in "
        "[PLAN.md](PLAN.md) Phase 9."
    )
    lines.append("")
    lines.append(
        f"**{len(manifests)} datasets migrated** · {human_size(total)} total · "
        f"{permitted} permitted / {restricted} restricted redistribution"
    )
    lines.append("")
    lines.append("| Dataset | Class | Source | Licence | Redist. | Integrity | Builder | Size | Used by |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for m in manifests:
        fn = m["filename"]
        title = oneline(m.get("title", ""))
        dataset = f"[**{fn}**]({RAW}/{fn})"
        if title:
            dataset += f"<br><sub>{title}</sub>"
        license = m.get("license") or {}
        row = [
            dataset,
            m.get("class", "?"),
            fmt_source(m.get("source")),
            oneline(license.get("name", "?")),
            fmt_redist(license),
            fmt_integrity(m.get("integrity")),
            fmt_builder(m),
            human_size(m["_size"]) if m["_size"] is not None else "—",
            fmt_consumers(m.get("consumers")),
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "**Legend** — *Integrity* is the `integrity.upstream.status` (is this "
        "what the source says?): ✅ verified · ◑ spot-checked · ⚠️ unverifiable · "
        "… unverified · ❌ failing. *Redist.* ⚠️ restricted files are cached as "
        "inherited exposures and tracked for licence review "
        "([workspace-lectures#20](https://github.com/QuantEcon/workspace-lectures/issues/20)). "
        "*Builder* ⚠️ unrecovered marks a constructed dataset whose builder was "
        "never committed (PLAN Phase 9)."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    manifests = load_manifests()
    if not manifests:
        print("no manifests found under lectures/*.yml", file=sys.stderr)
        return 1
    OUT.write_text(build(manifests), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} — {len(manifests)} datasets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
