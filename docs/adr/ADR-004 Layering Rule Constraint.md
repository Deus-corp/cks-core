# ADR-004

# Layering Rule Constraint: Enforcing Architectural Dependency Direction

**Status:** Proposed

**Date:** 2026-08-04

**Category:** Architecture Decision Record

---

# Context

The CKS ecosystem has a documented layering: `cks-core` (semantic
engine) ← `cks-runtime` (operational layer) ← `cks-mcp` (protocol
layer). Dependencies must flow in one direction only, enforced today by
`pyproject.toml` and developer discipline. However, nothing in the
knowledge graph itself mechanically prevents a future `evolve_knowledge`
call from adding a `depends_on` relation in the wrong direction (e.g.,
`cks-core → depends_on → cks-runtime`), creating a cycle that violates
the architecture but passes all existing constraints.

# Decision

Add `LayeringRuleConstraint` as a new opt-in constraint in
`cks.constraints.layering`. It checks every `depends_on` relation
against a configured layering order and raises an `ERROR` diagnostic
when a dependency points upstream instead of downstream.

The layering order is hardcoded for the CKS ecosystem:
`cks-core < cks-runtime < cks-mcp`. A future ADR could make this
configurable per deployment, but the CKS ecosystem's own layering
is a property of the project, not of individual deployments.

## Consequences

- Any `depends_on` relation added in the wrong direction is now
  mechanically rejected by `validate_knowledge` / `evolve_knowledge`
  when the extension is requested.
- The experiment that found this gap (Claude Desktop trying to add a
  reverse dependency) would now be caught automatically.