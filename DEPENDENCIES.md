# Dependency inventory

## Python runtime

Third-party runtime dependencies: **none**. The package and tests use only the
Python standard library. Minimum Python version: 3.11.

CI checks the declared minimum (3.11) and each currently targeted newer minor
(3.12 through 3.14) to catch standard-library/runtime compatibility changes.
This is a compatibility matrix, not a claim that every future Python release
has been tested.

## Build and installation

There is no wheel/editable-install build step in this v0.1 source release. Run from the
repository root using the commands in README. This avoids introducing a
build-backend dependency before a stable public package contract exists.

## CI actions

The GitHub Actions workflow uses two upstream actions pinned to full
commit identifiers:

| Action | Upstream release | Commit | Purpose | Update policy |
|---|---|---|---|---|
| actions/checkout | v7.0.1 | 3d3c42e5aac5ba805825da76410c181273ba90b1 | Read-only source checkout | Review upstream release and verify repository-owned tag before changing SHA |
| actions/setup-python | v7.0.0 | 5fda3b95a4ea91299a34e894583c3862153e4b97 | Select Python matrix versions | Review upstream release and verify repository-owned tag before changing SHA |

These are workflow dependencies, not Python runtime packages. Their transitive
implementation dependencies are maintained by their upstream repositories;
this candidate does not vendor them or claim a complete transitive action SBOM.

## SBOM status

EQUIVALENT_DEPENDENCY_INVENTORY: this file. A generated package SBOM was not
added because there are no third-party runtime packages and no existing safe
SBOM tool was needed to establish that fact.
