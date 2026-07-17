#!/usr/bin/env python3
"""Go-live guardrail: a PR must not break a file a live lecture consumes.

For every manifest sidecar lectures/<datafile>.yml:

  - the manifest's `filename` must match the sidecar's own name
  - if `consumers` is non-empty (a lecture reads this file in production):
      * the data file must exist
      * `integrity.sha256` must be recorded
      * the committed bytes must hash to it

Files with no manifest yet (Phase 6 backfill pending) or an empty `consumers`
list are out of scope here — the full validation suite (schema, dtypes,
invariants) is PLAN Phase 5 and will subsume this check.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

import yaml

LECTURES = pathlib.Path(__file__).resolve().parents[2] / "lectures"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    errors = []
    manifests = sorted(LECTURES.glob("*.yml"))
    checked = 0

    for manifest_path in manifests:
        manifest = yaml.safe_load(manifest_path.read_text())
        declared = manifest.get("filename")
        expected = manifest_path.name[: -len(".yml")]
        if declared != expected:
            errors.append(
                f"{manifest_path.name}: `filename: {declared}` does not match "
                f"the sidecar's own name (expected {expected!r})"
            )
            continue

        consumers = manifest.get("consumers") or []
        if not consumers:
            continue  # nothing live reads it — out of scope for this guardrail

        checked += 1
        data_path = LECTURES / declared
        if not data_path.exists():
            errors.append(
                f"{declared}: consumed by {len(consumers)} lecture(s) but the "
                f"data file is missing — this would break a live lecture build"
            )
            continue

        recorded = (manifest.get("integrity") or {}).get("sha256")
        if not recorded:
            errors.append(
                f"{declared}: consumed but integrity.sha256 is not recorded — "
                f"a consumed file must carry its hash so changes are deliberate"
            )
            continue

        actual = sha256(data_path)
        if actual != recorded:
            errors.append(
                f"{declared}: bytes do not match the manifest (sha256 {actual} "
                f"!= recorded {recorded}). If this is a deliberate in-place "
                f"correction, update integrity.sha256 in the same PR and plan "
                f"rebuilds for its consumers (AGENTS.md, 'Corrections vs "
                f"vintages')"
            )

    for e in errors:
        print(f"::error::{e}")
    print(
        f"{len(manifests)} manifest(s) found, {checked} consumed file(s) "
        f"checked, {len(errors)} error(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
