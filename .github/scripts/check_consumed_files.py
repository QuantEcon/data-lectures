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

Separately, for every file in sources/ (builder inputs, never served, no
manifest — sources/README.md is their audit trail):

  - the LFS rule must actually capture it
  - sources/README.md must record its sha256, under a `## <filename>` heading
  - the committed bytes must hash to that value

Same principle as the manifest gate above, keyed on the README instead: hash
whenever a hash is recorded. Without it, sources/ would carry no validation of
any kind while every file in lectures/ is validated as it migrates — and
SCF_plus.dta is the provenance root for two published datasets, so if its bytes
drifted both would become unreproducible and nothing would notice.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
LECTURES = REPO / "lectures"
SOURCES = REPO / "sources"

# One builder per published dataset, in builders/ (AGENTS.md, "Builders").
# `committed` asserts a runnable four-stage builder; `committed-frozen` says the
# builder is here and deliberately will not run (a frozen vintage, a scraper we
# will not re-run); `unrecovered` says it is absent; `not-applicable` is for
# verbatim files.
BUILDER_STATUSES = {"committed", "committed-frozen", "unrecovered", "not-applicable"}


SHA256_RE = re.compile(r"\b([0-9a-f]{64})\b")
# A `sources/` entry is a `## <filename>` section. Requiring the heading to look
# like a filename is what keeps a prose section from being read as one: the
# README has several, and a sha256 quoted in an example inside any of them would
# otherwise register as a recorded file and fail the no-such-file check below.
SOURCE_HEADING_RE = re.compile(r"^[\w.\-]+\.\w+$")
# An LFS pointer is <200 bytes of text whose second line is `oid sha256:<hex>`.
# That oid IS the object's sha256, which is what makes this check work under
# `lfs: false` — the real bytes are never fetched and never need to be.
#
# Line endings are tolerated rather than pinned. `.gitattributes` sets `-text` on
# sources/** so git does no conversion, and CI is ubuntu — but if a pointer ever
# did pick up a CR or a stray trailing newline, a stricter pattern would fall
# through to hashing the pointer text and report "committed bytes do not match"
# for an object that is perfectly correct. Still far too tight for any real
# data file to match by accident.
LFS_POINTER_RE = re.compile(
    rb"\Aversion https://git-lfs\.github\.com/spec/v1\r?\n"
    rb"oid sha256:([0-9a-f]{64})\r?\n"
    rb"size (\d+)\s*\Z"
)


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
            # Explicit encoding: manifests carry em-dashes and non-ASCII source
            # names, and read_text() otherwise decodes with the platform locale.
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
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
        # builder must name it, and the path it names must be a file in this
        # repo. Nothing else validates any of this — build_audit only records
        # the value and the catalog only formats it — so a manifest can assert
        # a builder that was never committed, or that has been moved.
        #
        # Types are checked first because YAML will hand us a list or a mapping
        # for either field, and both would raise rather than report: `status not
        # in BUILDER_STATUSES` is a TypeError on an unhashable value, and
        # `REPO / builder` is a TypeError on anything but a string.
        status = manifest.get("builder_status")
        builder = manifest.get("builder")
        if status is not None and not isinstance(status, str):
            errors.append(
                f"{declared}: builder_status must be a string, got "
                f"{type(status).__name__}"
            )
        elif status is not None and status not in BUILDER_STATUSES:
            errors.append(
                f"{declared}: unknown builder_status {status!r} — expected one "
                f"of {', '.join(sorted(BUILDER_STATUSES))}"
            )
        elif isinstance(status, str) and status.startswith("committed") and not builder:
            errors.append(
                f"{declared}: builder_status is {status!r} but no builder is "
                f"named — a dataset claiming a committed builder must say "
                f"where it is"
            )

        if builder is not None and not isinstance(builder, str):
            errors.append(
                f"{declared}: builder must be a string path, got "
                f"{type(builder).__name__}"
            )
        elif builder:
            # Resolve before checking: `REPO / builder` silently discards REPO
            # when builder is absolute, and a relative path can climb out with
            # `../`. Either way the assertion would be satisfied by a file that
            # is not a builder in this repo, which is the only thing it exists
            # to establish. A directory passes `.exists()` too, hence is_file.
            target = (REPO / builder).resolve()
            if not target.is_relative_to(REPO) or not target.is_file():
                errors.append(
                    f"{declared}: builder {builder!r} must be a file inside "
                    f"this repo — builders live in builders/<stem>.<ext> "
                    f"(AGENTS.md, 'Builders')"
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

    checked += check_sources(errors)

    for e in errors:
        print(f"::error::{e}")
    print(
        f"{len(manifests)} manifest(s) found, {checked} file(s) hash-checked, "
        f"{len(errors)} error(s)"
    )
    return 1 if errors else 0


def lfs_tracked(path: pathlib.Path) -> tuple[bool, str | None]:
    """Whether the LFS rule captures `path`, per .gitattributes.

    Returns (tracked, error). A git failure must NOT come back as `False`: an
    empty stdout would then read as "not captured by the LFS rule", which is
    the one catastrophe this check exists to report. A broken environment
    reporting the disaster it is meant to detect is worse than no check, so it
    gets its own message.
    """
    rel = path.relative_to(REPO).as_posix()
    try:
        out = subprocess.run(
            ["git", "check-attr", "filter", "--", rel],
            cwd=REPO, capture_output=True, text=True,
        )
    except OSError as exc:                       # git absent entirely
        return False, f"could not run `git check-attr` ({exc})"
    if out.returncode != 0:
        detail = out.stderr.strip().splitlines()
        return False, (
            f"`git check-attr` exited {out.returncode}"
            + (f" — {detail[0]}" if detail else "")
        )
    return out.stdout.strip().endswith(": lfs"), None


def check_sources(errors: list[str]) -> int:
    """Verify sources/ against the sha256 values in sources/README.md.

    Two assertions per file. The LFS one is not ceremony: SCF_plus.dta sits
    923,507 B (0.88%) under GitHub's hard blob limit, so a mis-scoped
    .gitattributes does not error — the push succeeds as plain git and the blob
    is in history permanently. That failure is silent in the one direction that
    cannot be undone, so it is worth a check rather than a convention.
    """
    if not SOURCES.is_dir():
        return 0

    readme = SOURCES / "README.md"
    if not readme.exists():
        errors.append(
            "sources/README.md is missing — it is the audit trail for a "
            "directory whose files carry no manifest (AGENTS.md, 'LFS, and "
            "sources/ vs lectures/')"
        )
        return 0

    # `## <filename>` starts a section; the first 64-hex token inside it is that
    # file's recorded sha256. Parsed by section rather than by table cell so the
    # README stays free to change its formatting. Headings that are not
    # filename-shaped are prose and are skipped — see SOURCE_HEADING_RE.
    sections = re.split(r"^## +", readme.read_text(encoding="utf-8"), flags=re.M)[1:]
    recorded: dict[str, str] = {}
    for sec in sections:
        name = sec.splitlines()[0].strip().strip("`")
        if not SOURCE_HEADING_RE.match(name):
            continue
        if m := SHA256_RE.search(sec):
            recorded[name] = m.group(1)

    files = sorted(p for p in SOURCES.iterdir() if p.is_file() and p.name != "README.md")
    checked = 0

    for path in files:
        tracked, git_error = lfs_tracked(path)
        if git_error:
            errors.append(
                f"sources/{path.name}: {git_error}. This is a tooling failure, "
                f"not a finding about the file — the LFS assertion could not be "
                f"evaluated either way"
            )
        elif not tracked:
            errors.append(
                f"sources/{path.name}: not captured by the LFS rule — "
                f"`git check-attr filter` does not say `lfs`. Everything under "
                f"sources/ must be LFS-tracked; a mis-scoped rule commits the "
                f"real bytes as plain git and does not error below 100 MiB"
            )

        want = recorded.get(path.name)
        if not want:
            errors.append(
                f"sources/{path.name}: no sha256 recorded in sources/README.md "
                f"— add a `## {path.name}` section with its origin, retrieval, "
                f"licence, sha256 and consuming builder"
            )
            continue

        # Under `lfs: false` the working file IS the pointer, and the pointer's
        # oid is the object's sha256 — so this verifies the real bytes without
        # fetching ~100 MiB of them. With LFS smudge on locally it is the real
        # file, and hashing it gives the same answer.
        blob = path.read_bytes() if path.stat().st_size < 1024 else None
        if blob is not None and (m := LFS_POINTER_RE.match(blob)):
            actual, kind = m.group(1).decode(), "LFS pointer oid"
        else:
            actual, kind = sha256(path), "committed bytes"

        checked += 1
        if actual != want:
            errors.append(
                f"sources/{path.name}: {kind} {actual} does not match the "
                f"sha256 recorded in sources/README.md ({want}). This file is "
                f"a builder input, so a drift here makes its outputs "
                f"unreproducible — update the README in the same PR if the "
                f"change is deliberate"
            )

    for name in sorted(set(recorded) - {p.name for p in files}):
        errors.append(
            f"sources/README.md records `{name}`, which is not in sources/ — "
            f"a stale audit-trail entry is worse than none"
        )

    return checked


if __name__ == "__main__":
    sys.exit(main())
