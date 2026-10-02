# Threat model

## Protected assets

- The controller's narrow A0 effect policy.
- The configured local workspace and the one note file written by the example.
- Correct correlation between a request and its returned result.
- The distinction between observed, unknown, and contradictory evidence.

## Trusted components and assumptions

- The local controller and the ProjectPolicy object are trusted to be
  constructed from the operator's intended policy.
- The Python interpreter, process, operating-system account, and configured
  workspace are trusted.
- The example adapter writes a fixed filename and does not execute commands.
- The Gateway is expected to be the only route used by the included example
  when a requester asks for an effect.

## Untrusted input

- Proposal fields from a provider or agent.
- Requested tool/capability labels.
- ToolRequest fields until the Gateway validates them.
- Any self-asserted identity, approval, role, authority, or trust metadata.

## Boundary behavior

- JSON structures are copied and bounded before canonical serialization; the
  public limits are documented in `CLAIMS_AND_LIMITATIONS.md`.
- Evidence aggregation accepts only built-in list/tuple containers of at most
  64 exact `EvidenceAssertion` values, and bounds string-field input by the
  documented per-string and aggregate limits. Invalid inputs remain UNKNOWN.
- Ill-formed Unicode is rejected before a digest can authorize or correlate an
  effect. Valid Unicode is encoded deterministically as UTF-8 without Unicode
  normalization.
- Unknown proposal fields and authority-like keys are rejected.
- Accepted proposal provenance remains DECLARED_UNVERIFIED; proposal
  admission never issues a grant or effect request.
- The Gateway permits only an exact configured A0 operation/capability pair
  for the configured workspace.
- Identity claims are not part of the policy decision.
- Denials happen before adapter invocation.
- A result whose effect outcome is ambiguous remains UNKNOWN; the Gateway
  does not automatically call the adapter again.
- Conflicting evidence remains CONTRADICTORY; missing or unreferenced
  evidence remains UNKNOWN.

## Excluded attackers and claims

This prototype does not protect against a compromised controller, arbitrary
malicious code in the same Python process, an operating-system administrator,
or a hostile actor able to race modifications to the local workspace. It has
no user authentication, cryptographic identity binding, hard OS isolation,
remote provider, cloud credentials, durable ledger, or cross-process recovery.
Filesystem durability and distributed exactly-once semantics are not claimed.

The in-process request cache limits duplicate adapter calls only while the same
Gateway instance remains alive. A crash after the adapter effect but before a
result is observed can leave the effect state unknown; a later process cannot
reconcile that state in this V0.1.

A process-control interruption such as `KeyboardInterrupt` can also escape
after an adapter effect but before the in-memory result is recorded. If the
caller catches the interruption and continues in the same process, resubmitting
the same request may invoke the adapter again. The caller must treat that
outcome as unknown rather than infer that the effect did not occur.

The request-result cache has no process-lifetime entry quota, and the example's
append-only note file has no cumulative storage quota. Repeated unique requests
or authorized appends can therefore exhaust local memory or disk. These two
LOW availability risks are accepted only for finite, trusted, local
experimental v0.1 use. They are not accepted for continuous service, untrusted
input, multi-user or multi-caller deployments, or long-running/high-volume
use; reopen the design and add/test appropriate bounds before entering those
envelopes.
