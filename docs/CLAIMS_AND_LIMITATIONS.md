# Claims and limitations

Claims are scoped to this candidate and its deterministic tests.

## Input bounds and canonical encoding

`canonical_json` validates and copies JSON-compatible data before encoding it.
The bounded public contract is:

- Canonical UTF-8 representation: at most 320 KiB (327,680 bytes).
- Individual string: at most 8,192 Unicode code points.
- Object or array: at most 64 entries/items.
- Nested container depth: at most 32.
- JSON values and object keys combined: at most 4,096 nodes.
- Integer values: at most 24,576 bits; non-finite floats are rejected.

The proposal schema further limits each requested-tools/capabilities array to
16 items, objective text to 2,000 characters, and metadata to 8 KiB. Valid
Unicode is encoded as UTF-8 exactly as supplied; no Unicode normalization is
performed. Ill-formed Unicode, cyclic structures, and values outside these
bounds receive a typed rejection before the Gateway can invoke the adapter.
These limits describe this local candidate boundary only; they are not a
network-service or process-isolation guarantee.

| Claim | Class | Meaning |
|---|---|---|
| External proposal admission does not grant authority or create an effect request | SUPPORTED_BOUNDED | Verified by focused unit tests for valid requests, requested tools, nested authority fields, and no effect path. |
| The included Gateway mediates the fixed local note operation | SUPPORTED_BOUNDED | Exact workspace, operation, and capability must match controller-supplied A0 policy; the adapter is not called on denial. |
| Results are correlated to request ID and canonical request digest | SUPPORTED_BOUNDED | Demonstrated by the local example and tests within one process. |
| Same-instance repeated request IDs do not invoke the adapter again | EXPERIMENTAL | A completed call or ordinary adapter `Exception` is memoized only in the live instance; this does not cover a `BaseException` interruption after an effect but before result memoization, and is not durable across process restart. |
| The Gateway does not automatically retry an ambiguous adapter error | SUPPORTED_BOUNDED | An ordinary adapter `Exception` produces UNKNOWN and is memoized in the live instance. If a process-control interruption escapes after an effect but before memoization, a caller that catches it and resubmits the request may invoke the adapter again; the caller must not infer that no effect occurred. Restart recovery is not provided. |
| Evidence aggregation does not promote missing or contradictory evidence | SUPPORTED_BOUNDED | The helper returns UNKNOWN for missing, malformed, or over-limit input and CONTRADICTORY for conflicting observed values. It does not prove the truth of a claim. Input is limited to 64 assertions, 8,192 code points per string, and 320 KiB total JSON-escaped UTF-8 string-field data. |
| JSON input is bounded before canonical serialization and snapshotting | SUPPORTED_BOUNDED | The public canonicalization path rejects inputs over the documented byte, string, collection, nesting, or node limits; focused tests cover each boundary. |
| Ill-formed Unicode does not produce a digest or effect | SUPPORTED_BOUNDED | Lone high/low surrogates are rejected with a typed admission/Gateway result; valid UTF-8 strings retain deterministic canonical digest behavior. |
| A0 policy is the only accepted policy level | SUPPORTED_BOUNDED | The data type rejects another declared level. It does not authenticate who constructed the policy or prove human authorization. |
| Hard isolation, host-admin resistance, or arbitrary same-process compromise protection | NOT_PROVEN | Excluded from this local Python reference. |
| Distributed exactly-once, durable replay, multi-host recovery, or production HA | OUT_OF_SCOPE | Explicitly not implemented or claimed. |
| A1 autonomy, generic shell/browser tools, model serving, provider integrations, or worker fleets | OUT_OF_SCOPE | Not in the V0.1 candidate. |
| End-to-end integration with private FioOS Runtime Gateway | NOT_PROVEN | This candidate is a small reference rewrite and is not a drop-in extraction of the coupled private runtime. |

## Local availability limitations

This prototype does not impose a process-lifetime entry limit on the
Gateway's in-memory request-result cache, or a cumulative byte quota on
`notes.jsonl`. Individual requests are bounded, but repeated unique requests
can grow memory and repeated authorized appends can grow local storage. The
candidate is intended for bounded, trusted local experiments, not an
untrusted multi-caller or long-running service. These availability limits are
accepted only for finite, trusted, local experimental use in v0.1. They are
not acceptable assumptions for continuous service, untrusted input,
multi-user or multi-caller deployments, or long-running/high-volume use.
Before entering any of those envelopes, reopen the design and add/test
appropriate cache bounds and storage quotas; do not infer that this release
is safe for those use cases.

An interruption derived from `BaseException` (for example, `KeyboardInterrupt`)
can escape the adapter call before its result is memoized. If the caller keeps
the process alive and resubmits that request, the local effect may run again.
This interruption window is not covered by the same-instance replay claim; an
absent result is not evidence that no effect occurred.

OBSERVED evidence means the program recorded a bounded observation. It is not
equivalent to TRUE, VERIFIED, or SAFE_TO_CONTINUE for arbitrary semantic
claims.
