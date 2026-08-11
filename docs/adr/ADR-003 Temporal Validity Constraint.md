# ADR-003

# Temporal Validity Constraint: Time-Bounded Fact Semantics

**Status:** Proposed

**Date:** 2026-08-04

**Category:** Architecture Decision Record

---

# Context

`cks-core` has constraints for ontology (`type_hierarchy`), reasoning
(`inference_confidence_conflict`, `supersession_chain`), and provenance
(`verification_record`), but no built-in notion of temporal validity --
the fact that a claim may be true only within a certain time window.
`InferenceStalenessSweeper` (cks-runtime, ADR-009) detects stale
*inference steps*, but `cks-core` itself has no semantic primitive for
"this claim is valid until T".

# Decision

Add `TemporalValidityConstraint` as a new opt-in constraint in
`cks.constraints.temporal`. It checks every object's `structure` for an
optional `valid_until` field (ISO-8601 datetime string). If present and
in the past, a `WARNING` diagnostic is raised: the fact is still
structurally valid (no ERROR), but its temporal window has closed.

This is deliberately minimal -- no reasoning about time intervals,
Allen's algebra, or temporal logic. It answers exactly one question:
"has this fact expired?", which is the foundation for a future
`TemporalStalenessSweeper` (cks-runtime) that would periodically
re-check expired facts, the same way `InferenceStalenessSweeper` does
for inference steps.

## Consequences

- Any object can now carry `valid_until` in its structure; the constraint
  flags expired ones as `WARNING` when opted into via `extensions`.
- Unblocks a `temporal_staleness_sweeper` in cks-runtime (future ADR).
- No breaking change: the field is optional and the constraint is opt-in.