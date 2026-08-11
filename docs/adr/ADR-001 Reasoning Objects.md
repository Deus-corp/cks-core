# ADR-001

# Reasoning Objects: Inference as a First-Class, Opt-In Extension

**Status:** Proposed

**Date:** 2026-07-31

**Category:** Architecture Decision Record

---

# Context

`cks-core` already records, precisely and verifiably, *what* a
Knowledge Structure looks like at every version: `StructuralOperator`
subclasses (`AddObject`, `AddRelation`, `UpdateObject`, ...) each
carry a formal `OperatorContract`, and `cks-runtime` versions every
application of one. `cks-mcp` layers provenance (`verify_source`,
`VerificationRecordIntegrityConstraint`) on top of that, so a claim's
*data source* is signed and checkable.

None of this records *why* an object or relation was asserted in the
first place — which premises an agent read, which inference rule or
heuristic it applied, how confident it was, or what alternative it
rejected. That reasoning currently lives only in the LLM's ephemeral
context window (if anywhere), which means it is not versioned, not
mergeable, not queryable, and does not survive the session boundary
that `export_session` / `fork_sandbox` otherwise preserve for
everything else in the graph.

This is `cks-core`'s first ADR — the repo has no `docs/adr/`
precedent the way `cks-runtime` and `cks-mcp` already do. This
document follows their existing template.

This proposal follows the convention `contradiction.py` already
established for `ontology.py`/`projection.py`/`verification.py`: the
rules for a new concern are ordinary Knowledge Objects declared
*inside* the graph, not external configuration, and the constraint
that reads them is an **opt-in extension**, not a normative
`CKS-001..CKS-008` constraint.

---

# Problem

Three concrete gaps follow from reasoning having no representation:

1. **No queryable provenance of inference.** `verify_source` proves
   *where a fact came from*; nothing proves *how a conclusion was
   derived* from facts already in the graph.
2. **`detect_contradictions` only sees data-level conflicts.**
   `MutualExclusionConstraint` / `FunctionalRelationConstraint` flag
   two relations that are jointly nonsensical, but have no notion of
   confidence — two agents whose *inferences* disagree get a hard
   contradiction instead of a resolvable, confidence-weighted belief
   conflict.
3. **`explain_diff` / `explain_knowledge` have no native "why."**
   They can describe what changed structurally, but can only guess at
   justification by re-reading surrounding structure.

---

# Decision (proposed)

## 1. `InferenceStep` as an ordinary `KnowledgeObject` — no core.py changes

An inference step is a `KnowledgeObject` whose `identity.type ==
"InferenceStep"` (a reserved vocabulary word, exactly like
`MutualExclusionRule` / `FunctionalRelationRule` already are), with
`structure`:

```json
{
  "premises": ["<object_id>", "..."],
  "conclusion": "<object_id>",
  "operator": "deductive | inductive | abductive | heuristic",
  "confidence": 0.0,
  "justification": "<short free text>",
  "alternatives_considered": ["<short free text>", "..."],
  "superseded_by": null
}
```

**Why an object, not a relation:** `CanonicalRelation.participants`
is a flat, arity-based list with no role labels — `contradiction.py`
already notes it only reasons about ordered `(source, target)` pairs.
Packing N premises + 1 conclusion into `participants` would either
lose the premise/conclusion distinction or invent a positional
convention no other `relation_type` uses. A typed object with named
structure fields keeps `premises`/`conclusion` first-class and
leaves `ontology.py`'s relation-typing machinery untouched.

## 2. New opt-in extension module: `cks/constraints/reasoning.py`

Following `contradiction.py`'s precedent exactly — not in
`BUILTIN_CONSTRAINTS`, opt in via `OPTIONAL_CONSTRAINTS`:

- `InferenceReferentialIntegrityConstraint` — every id in an
  `InferenceStep`'s `premises`/`conclusion` must reference an object
  that exists in the structure (same shape as
  `NoDanglingRelationConstraint`, scoped to this type).
- `ConfidenceBoundsConstraint` — `confidence` must be a float in
  `[0, 1]`.
- `SupersessionChainConstraint` — if `A.superseded_by == B`, `B` must
  target the same `conclusion` id, so revision chains stay coherent.

Registered in `OPTIONAL_CONSTRAINTS_BY_NAME` as
`"inference_referential_integrity"`, `"confidence_bounds"`,
`"supersession_chain"`, matching existing naming.

## 3. Convenience operator: `RecordInference(StructuralOperator)`

A thin wrapper over the same mechanism `AddObject` uses (an
`InferenceStep` is a plain `KnowledgeObject`), but with a
purpose-built `OperatorContract` whose preconditions state the
`InferenceStep`-specific obligations, and which — like `AddRelation`
already does for its participants — eagerly checks premise/conclusion
existence in `_mutate`, not only at validation time. Registered in
`parse_operations` as op type `"record_inference"`, so `cks-runtime`
and `cks-mcp` get it through the existing wire-format channel with no
adapter-specific code.

## 4. Downstream consumers — no ADR needed there, just usage

- `explain_knowledge` / `explain_diff` (`cks-mcp`) walk `InferenceStep`
  objects the same way they already walk any `KnowledgeObject`.
- `detect_contradictions` gets a natural, later extension point (out
  of scope here): two `InferenceStep`s with the same `conclusion` but
  disagreeing `confidence` is now a queryable pattern instead of an
  unrepresentable one.
- `cks-runtime`'s operation log and version history store
  `RecordInference` like any other operator, so reasoning steps get
  branching and three-way merge for free — an `InferenceStep` is just
  an object with an id.

---

# Non-Goals

- No automatic inference engine, theorem proving, or confidence
  propagation algebra. This ADR reifies the *record* of an inference
  an external agent already performed; it does not have `cks-core`
  derive new conclusions itself.
- No change to `CanonicalRelation`, `ObjectIdentity`, or existing
  wire-format operation types — `"record_inference"` is additive.

---

# Alternatives Considered

- **A new core dataclass alongside `KnowledgeObject`/`CanonicalRelation`.**
  Rejected: would ripple through `core.py`'s hashing, `KnowledgeStructure`
  indexing, serialization, and every consumer that pattern-matches on
  `isinstance(obj, CanonicalRelation)` (e.g. `RemoveObject`'s cascade
  in `evolution.py`). A typed `KnowledgeObject` costs zero core changes.
- **A `CanonicalRelation` with `relation_type="infers"`.** Rejected
  for the participants-arity reason above.

---

# Consequences

- `cks-core` gains its first `docs/adr/` entry.
- Fully additive: a structure with no `InferenceStep` objects is
  unaffected, matching every other extension's convention in this
  package.
- Lays the groundwork for portable "cognition checkpoints" across
  `cks-mcp` sessions — an exported session can round-trip *reasoning*,
  not only facts, once producers start emitting `RecordInference`.
