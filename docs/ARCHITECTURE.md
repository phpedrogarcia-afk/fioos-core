# Architecture

## Deliberately narrow path

    provider or local agent
        -> external proposal admission (data only)
        -> trusted controller creates a typed ToolRequest
        -> RuntimeGateway checks local A0 policy
        -> one fixed local note adapter
        -> correlated ToolResult / receipt

Admission never creates a ToolRequest. Requested tools and capabilities stay
as declarations on the proposal. The controller chooses a request separately;
the Gateway checks that exact operation, capability, and workspace against
its controller-supplied policy.

An identity_claim is carried as correlation/context and included in the
request digest. The policy does not consult it, and it cannot grant access.

## Public modules

- fioos_core.contracts: proposal, provenance, ToolRequest, ToolResult, and
  evidence-state contracts.
- fioos_core.policy: immutable A0-only policy and exact effect grants.
- fioos_core.gateway: request validation, policy enforcement, local
  same-instance replay handling, and the fixed note adapter.

Public entry point: RuntimeGateway.execute(ToolRequest). The only concrete
adapter in this candidate appends one JSON record to a fixed filename under a
configured local workspace. No shell, network, provider SDK, database, or
cloud adapter is included.

## Trust boundary

The Gateway is the intended boundary between a requesting agent and the
included effect adapter. This is a software design boundary inside one Python
process, not a sandbox against malicious Python code in that process. The
controller, policy object, adapter construction, and operating-system user
are trusted for this example.

The request cache is in memory and scoped to one RuntimeGateway instance.
After process restart, this implementation cannot know whether a prior local
effect happened. It therefore does not claim durable replay protection or
distributed exactly-once behavior.

## Accepted v0.1 availability risks

For finite, trusted, local experimental use only, v0.1 accepts two LOW
availability risks: unique request IDs can grow the in-memory cache without a
process-lifetime quota, and authorized appends can grow `notes.jsonl` without
a cumulative storage quota. These are not accepted for continuous service,
untrusted input, multi-user or multi-caller deployments, or long-running or
high-volume use. Reopen the design and add/test bounds before entering any of
those envelopes.
