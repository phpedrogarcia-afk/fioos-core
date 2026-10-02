# FioOS Experimental Governance Runtime

FioOS is an experimental, provider-independent governance and effect-control
layer for AI agents. It focuses on separating project policy from agent
capability, routing bounded effects through a Runtime Gateway, and preserving
request/result provenance without turning missing information into certainty.

This experimental v0.1 release is a small local reference core, not the private
FioOS laboratory and not a production security product. It demonstrates one A0,
single-process, local file-append effect. It does not provide shell execution,
cloud access, model calls, or a general agent framework.

## Who it is for

For people experimenting with the governance boundary around agents supplied
by Codex, Antigravity, the Agents API, or another provider. A provider can
produce a proposal; it does not become the source of project authority.

FioOS complements rather than replaces Codex, Antigravity, the Agents API, or
their reasoning, tooling, and user experience. This repository is not a
generic agent harness and does not claim those products lack their own
governance features.

## Run the example

Requirements: Python 3.11 or newer. There are no third-party Python runtime
dependencies and no paid API or cloud account is required.

From this directory:

    python -m unittest discover -s tests -v
    python -m examples.minimal

The example uses a deterministic local proposal fixture. It demonstrates an
untrusted proposal, a controller-created request, one bounded file effect
mediated by the Gateway, a denied shell-like request, and machine-readable
correlation evidence. Its temporary workspace is removed when the example
ends.

## What this does not do

It does not establish the identity of the person who created local policy,
protect a Python process from hostile code in that same process, provide OS
isolation, or make local in-memory replay protection durable. It does not
claim production-ready distributed exactly-once execution. It is not A1
autonomy, high availability, multi-host recovery, or a replacement for a real
deployment threat model.

Read docs/CLAIMS_AND_LIMITATIONS.md before relying on the example outside a
disposable local experiment. The two accepted LOW availability risks are an
unbounded process-lifetime request-result cache and an unbounded cumulative
local notes file. They are accepted only for finite, trusted local v0.1
experiments; this release is not suitable as a continuous, untrusted,
multi-user, or long-running service. See LICENSE for Apache-2.0 terms.
