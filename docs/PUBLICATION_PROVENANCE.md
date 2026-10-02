# Publication provenance review

This bounded review classifies the files in the v0.1 public source export. It
is a source-origin and inclusion review, not a comprehensive history audit or
independent legal opinion. The human project owner explicitly authorized
distribution of the included original FioOS material under Apache-2.0 and
confirmed, to the best of their knowledge, that no incompatible third-party
code is included. No private source coordinates or local filesystem paths
are included here.

## File-level inventory

| File | Classification | Basis and release note |
|---|---|---|
| `.gitignore` | GENERATED_FOR_PROJECT | Candidate-local Python/build exclusions; no third-party code. |
| `CHANGELOG.md` | GENERATED_FOR_PROJECT | v0.1 experimental release notes and explicit limits. |
| `CONTRIBUTING.md` | GENERATED_FOR_PROJECT | Contribution guidance for the experimental source release. |
| `DEPENDENCIES.md` | GENERATED_FOR_PROJECT | Dependency inventory; CI action references are external dependencies, not vendored implementation. |
| `LICENSE` | CANONICAL_LICENSE_TEXT | Unmodified Apache License 2.0 text, selected by explicit human-owner authorization. |
| `README.md` | GENERATED_FOR_PROJECT | Public description, usage, and limitations. |
| `SECURITY.md` | GENERATED_FOR_PROJECT | Security-reporting instructions that require verifying the repository's private reporting form. |
| `.github/workflows/ci.yml` | GENERATED_FOR_PROJECT | Public CI workflow; it invokes pinned upstream actions but contains no action source. |
| `docs/ARCHITECTURE.md` | GENERATED_FOR_PROJECT | Description of the implementation in this release. |
| `docs/CLAIMS_AND_LIMITATIONS.md` | GENERATED_FOR_PROJECT | Bounded claims tied to code and tests, including accepted availability risks. |
| `docs/PROVENANCE.md` | GENERATED_FOR_PROJECT | Sanitized extraction, human authorization, and review limits. |
| `docs/THREAT_MODEL.md` | GENERATED_FOR_PROJECT | Local threat model and exclusions. |
| `docs/PUBLICATION_PROVENANCE.md` | GENERATED_FOR_PROJECT | This bounded public-export inventory and review record. |
| `examples/__init__.py` | GENERATED_FOR_PROJECT | Package marker for the minimal example. |
| `examples/minimal.py` | GENERATED_FOR_PROJECT | Deterministic example for the local Gateway path. |
| `fioos_core/__init__.py` | GENERATED_FOR_PROJECT | Public package exports. |
| `fioos_core/contracts.py` | ADAPTED_WITH_ATTRIBUTION | Original narrow implementation re-expressing FioOS governance concepts; no third-party source was identified in this bounded review. |
| `fioos_core/gateway.py` | ADAPTED_WITH_ATTRIBUTION | Original local-only effect boundary re-expressing FioOS governance concepts; no third-party source was identified in this bounded review. |
| `fioos_core/policy.py` | ADAPTED_WITH_ATTRIBUTION | Original A0 policy example re-expressing FioOS governance concepts; no third-party source was identified in this bounded review. |
| `tests/test_contracts.py` | GENERATED_FOR_PROJECT | Deterministic tests for the public contracts. |
| `tests/test_gateway.py` | GENERATED_FOR_PROJECT | Deterministic tests for the public Gateway behavior. |
| `RELEASE-MANIFEST-v0.1.md` | GENERATED_FOR_PROJECT | Public source inventory and bounded release evidence. |

No file is classified `THIRD_PARTY_INCLUDED` or `UNKNOWN` after this bounded
candidate review. The review searched the candidate for copyright/license
headers, vendor markers, external source blocks, and private development
coordinates. The only external implementation references found are the
upstream CI actions listed in `DEPENDENCIES.md`; their code is not included.
`LICENSE` contains the unmodified canonical Apache License 2.0 text. The
upstream CI action code is fetched by GitHub Actions and is not included.

## Rights and limits

`THIRD_PARTY_INCLUDED_REQUIRING_UNRESOLVED_LICENSE=0` for the files reviewed.
`UNKNOWN_MATERIAL_FILE_PROVENANCE_BLOCKERS=0` for the same bounded inventory.
These classifications do not independently resolve historical ownership or
contributor rights beyond the human owner's explicit distribution
authorization. They are not a legal opinion. New included material requires a
fresh provenance and license review.

This review does not claim complete historical provenance, exhaustive global
similarity checking, legal advice, or permission to release. No external
donor-source attribution is asserted because no third-party source inclusion
or specific external-source derivation was established by this review.
