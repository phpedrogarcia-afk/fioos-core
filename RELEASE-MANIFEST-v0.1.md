# FioOS Public Core v0.1 Source Manifest

Status: authorized experimental v0.1.0 export. This manifest inventories the
public source; it is not, by itself, evidence that the GitHub publication or
release gates have completed. The export has no embedded private-repository
revision identity.

## Public source files

The reviewed candidate contains these 22 files:

- `.gitignore`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `DEPENDENCIES.md`
- `LICENSE`
- `README.md`
- `SECURITY.md`
- `.github/workflows/ci.yml`
- `docs/ARCHITECTURE.md`
- `docs/CLAIMS_AND_LIMITATIONS.md`
- `docs/PROVENANCE.md`
- `docs/PUBLICATION_PROVENANCE.md`
- `docs/THREAT_MODEL.md`
- `examples/__init__.py`
- `examples/minimal.py`
- `fioos_core/__init__.py`
- `fioos_core/contracts.py`
- `fioos_core/gateway.py`
- `fioos_core/policy.py`
- `tests/test_contracts.py`
- `tests/test_gateway.py`
- `RELEASE-MANIFEST-v0.1.md`

## Public modules and dependencies

Public Python package modules are `fioos_core.contracts`,
`fioos_core.policy`, and `fioos_core.gateway`. The local example is
`examples.minimal`.

Runtime dependencies: Python 3.11 or newer and the Python standard library;
third-party Python runtime dependencies: none. CI uses the two immutable
upstream GitHub Actions identified in `DEPENDENCIES.md`; their source is not
vendored. The deterministic test suite contains 36 tests in this candidate.

## Security scan disposition

The earlier bounded Codex Security Standard scan reported two LOW findings:
unbounded pre-canonicalization work on externally supplied structures and an
unhandled digest error for ill-formed Unicode. Both are fixed with bounded
snapshots and typed fail-closed results before effects. A later independent
review identified an input-validation gap in the exported evidence
aggregator; it is fixed with deterministic type, collection, string, aggregate
size, and Unicode checks, with focused tests. That review also identified two
local availability limitations: the in-memory request-result cache has no
process-lifetime entry quota, and `notes.jsonl` has no cumulative storage
quota. They are accepted only for finite, trusted, local experimental v0.1
use because adding eviction or quota behavior would change replay or storage
semantics. Continuous service, untrusted input, multi-user or multi-caller
deployment, and long-running/high-volume use are explicitly excluded. The bounded final candidate-specific Codex
Security scan reported partial workbench coverage because it did not generate
a discovery worklist. A separate fresh-context static review read all 22
source-inventory files. Across the reviewed surfaces, no Critical, High, or
Medium issue was reported; two LOW availability findings remain: the
per-instance result cache has no process-lifetime entry quota, and
`notes.jsonl` has no cumulative storage quota. Both are accepted with
justification only for finite, trusted, local experimental v0.1 use; neither
is a guarantee for continuous service, untrusted, multi-user, or long-running
use. Before entering any excluded envelope, reopen the design and add/test
appropriate cache bounds and storage quotas. The review also records that a
`BaseException` interruption after an effect but before result memoization may
leave the outcome unknown if a caller resumes and resubmits. The same-instance
replay claim is limited accordingly. This bounded review is not a production
security certification or a legal review.

## Provenance and license

The bounded file-level classifications and their limits are in
`docs/PUBLICATION_PROVENANCE.md`. That review found no included third-party
implementation source and no unknown material file-provenance blocker. The
human project owner explicitly authorized distribution of the included
original FioOS material under Apache-2.0 and confirmed, to the best of their
knowledge, that no incompatible third-party code is included. This is not an
independent legal opinion or a claim of complete historical provenance.

## Known limitations and non-goals

This is an experimental, local A0 reference implementation with one
single-process file-append effect. It is not a production security product,
generic agent harness, provider integration, shell or cloud executor, hard
isolation boundary, durable replay system, high-availability service, or
distributed exactly-once system. It does not authenticate the person who
constructed local policy and does not protect against malicious code inside
the same Python process. See `docs/CLAIMS_AND_LIMITATIONS.md` and
`docs/THREAT_MODEL.md` for the tested claim envelope.

## Post-publication configuration

Before the release is considered complete, enable and verify GitHub Private
Vulnerability Reporting or the closest available GitHub-native private
reporting feature. Record its actual status; do not imply a private channel is
active unless repository settings confirm it:

`POST_PUBLICATION_REQUIRED: ENABLE_GITHUB_PRIVATE_VULNERABILITY_REPORTING`

The final repository setting is reported with the publication evidence.

## Packaging note

The source preparation directory may contain generated Python bytecode ignored
by `.gitignore`. It is not part of the 22-file public inventory above. The
public export contains only the declared source inventory and must not be
replaced with a raw copy of the preparation directory.
