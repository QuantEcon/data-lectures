#!/usr/bin/env python3
"""Go-live guardrail: a PR must not break a file a live lecture consumes, and
must not land bytes that do not match what the manifest says they are.

For every manifest sidecar lectures/<datafile>.yml:

  - the manifest's `filename` must match the sidecar's own name
  - if `consumers` is non-empty (a lecture reads this file in production):
      * the data file must exist
      * `integrity.sha256` must be recorded
  - if `integrity.sha256` is recorded, with or without consumers:
      * the data file must exist
      * the committed bytes must hash to it
  - the builder record must be internally consistent:
      * `builder_status` must be a known value
      * a `committed*` status must name a builder
      * a named builder must exist on disk

The second clause exists because manifests land *ahead* of their repoints by
convention, so a dataset arrives with `consumers: []` and is flipped by a
later PR in another repo. Keying the hash check on `consumers` alone meant
the one PR that introduces new bytes was the one PR that never verified
them — and this is the repo's only byte-integrity gate.

Files with no manifest yet (Phase 6 backfill pending), and manifests that
record no hash, are out of scope here — the full validation suite (schema,
dtypes, invariants) is PLAN Phase 5 and will subsume this check.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
LECTURES = REPO / "lectures"

# One builder per published dataset, in builders/ (AGENTS.md, "Builders").
# `committed` asserts a runnable four-stage builder; `committed-frozen` says the
# builder is here and deliberately will not run (a frozen vintage, a scraper we
# will not re-run); `unrecovered` says it is absent; `not-applicable` is for
# verbatim files.
BUILDER_STATUSES = {"committed", "committed-frozen", "unrecovered", "not-applicable"}


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
        try:
            manifest = yaml.safe_load(manifest_path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{manifest_path.name}: invalid YAML — {exc}")
            continue
        if not isinstance(manifest, dict):
            errors.append(
                f"{manifest_path.name}: manifest must be a YAML mapping, got "
                f"{type(manifest).__name__} — is the file empty or malformed?"
            )
            continue

        declared = manifest.get("filename")
        expected = manifest_path.name[: -len(".yml")]
        if declared != expected:
            errors.append(
                f"{manifest_path.name}: `filename: {declared}` does not match "
                f"the sidecar's own name (expected {expected!r})"
            )
            continue

        # Builder: the status must be a known one, a dataset that claims a
        # builder must name it, and the path it names must exist. Nothing else
        # in the repo validates any of this — build_audit only records the
        # value and the catalog only formats it — so a manifest can currently
        # assert a builder that was never committed, or that has been moved.
        status = manifest.get("builder_status")
        builder = manifest.get("builder")
        if status is not None and status not in BUILDER_STATUSES:
            errors.append(
                f"{declared}: unknown builder_status {status!r} — expected one "
                f"of {', '.join(sorted(BUILDER_STATUSES))}"
            )
        elif str(status).startswith("committed") and not builder:
            errors.append(
                f"{declared}: builder_status is {status!r} but no builder is "
                f"named — a dataset claiming a committed builder must say "
                f"where it is"
            )
        if builder and not (REPO / builder).exists():
            errors.append(
                f"{declared}: builder {builder!r} does not exist — builders "
                f"live in builders/<stem>.<ext> (AGENTS.md, 'Builders')"
            )

        consumers = manifest.get("consumers") or []
        integrity = manifest.get("integrity")
        # A present-but-malformed integrity block must fail loudly. Read as
        # "no hash recorded" it would skip the byte check entirely for a
        # manifest that has no consumers yet — which is how every new dataset
        # lands here, since manifests precede their repoints.
        if integrity is not None and not isinstance(integrity, dict):
            errors.append(
                f"{declared}: `integrity` must be a mapping, got "
                f"{type(integrity).__name__} — check the indentation under "
                f"`integrity:`; as written the sha256 is unreadable and the "
                f"byte check would be skipped silently"
            )
            continue
        recorded = (integrity or {}).get("sha256")

        if not consumers and not recorded:
            continue  # nothing reads it, nothing to verify — out of scope

        data_path = LECTURES / declared
        if not data_path.exists():
            errors.append(
                f"{declared}: consumed by {len(consumers)} lecture(s) but the "
                f"data file is missing — this would break a live lecture build"
                if consumers else
                f"{declared}: integrity.sha256 is recorded but the data file "
                f"is missing — a manifest describes a file this repo publishes"
            )
            continue

        if not recorded:
            errors.append(
                f"{declared}: consumed but integrity.sha256 is not recorded — "
                f"a consumed file must carry its hash so changes are deliberate"
            )
            continue

        actual = sha256(data_path)
        checked += 1    # counted where the hash is actually computed
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
        f"{len(manifests)} manifest(s) found, {checked} file(s) hash-checked, "
        f"{len(errors)} error(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
