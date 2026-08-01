# ADR-002

# Belief Revision Support: Cascading Staleness and Entrenchment Ranking for InferenceStep

**Status:** Implemented (cks-core 1.17.0)

**Date:** 2026-08-01

**Category:** Architecture Decision Record

---

# Context

ADR-001 ("Reasoning Objects") introduced `InferenceStep` as an ordinary
`KnowledgeObject` — `premises`, `conclusion`, `operator`, `confidence`,
`justification`, `alternatives_considered`, `superseded_by` — plus four
opt-in constraints, already implemented in `cks/constraints/reasoning.py`
and registered in `OPTIONAL_CONSTRAINTS_BY_NAME`:

- `inference_referential_integrity`
- `confidence_bounds`
- `supersession_chain`
- `inference_confidence_conflict` — flags active (non-superseded)
  `InferenceStep`s that share a `conclusion` but disagree on
  `confidence`, as a WARNING

That last constraint already does the detection work ADR-001 named as
its natural next step for `detect_contradictions` — this ADR does not
repeat it. Two gaps remain once an agent actually tries to *act* on a
flagged conflict or a `superseded_by` chain:

1. `InferenceConfidenceConflictConstraint`'s message tells an agent a
   conflict exists and suggests resolving it with `RecordInference` +
   `superseded_by`, but nothing in `cks-core` helps decide *which*
   step should supersede which — an agent re-derives a ranking from
   raw `confidence` floats inline, every time, with no shared
   definition of "more entrenched."
2. `SupersessionChainConstraint` validates a chain that already
   exists (successor exists, is an `InferenceStep`, targets the same
   conclusion) but has no notion of *cascading* staleness: if every
   `InferenceStep` that concluded some object `X` becomes superseded,
   any other live `InferenceStep` that still lists `X` as a `premise`
   is now silently resting on a fully retracted belief, and nothing
   says so.
3. `SupersessionChainConstraint` also doesn't reject a cycle
   (`A.superseded_by == B`, `B.superseded_by == A`) — each pairwise
   check passes independently of the others.

---

# Decision (proposed)

## 1. `rank_by_entrenchment` — a pure query function, not a constraint

```python
def rank_by_entrenchment(
    structure: KnowledgeStructure, conclusion_id: str
) -> list[KnowledgeObject]:
    """Active InferenceSteps concluding `conclusion_id`, ordered
    highest-entrenchment first: confidence descending, then
    structure-declared order as a stable tiebreak. Returns [] if
    fewer than one active step exists -- there is nothing to rank."""
```

Lives in `cks/constraints/reasoning.py` next to the constraints it
supports, exported from `__all__`, but it is not a `Constraint`
subclass and produces no `Diagnostic` — calling it never changes a
validation outcome. Consumers (`cks-mcp`'s `explain_knowledge`,
`suggest_evolution`) call it only after `InferenceConfidenceConflictConstraint`
has already flagged a conflict, turning "here are the disagreeing
steps" into "here they are, ranked" for whichever agent — human or
LLM — makes the actual call. This ranks; it never writes
`superseded_by` itself, matching ADR-001's existing non-goal of
`cks-core` deriving conclusions on its own.

## 2. `StalePremiseConstraint` — new opt-in constraint, WARNING severity

**Revised during implementation** — the version below is what shipped;
see "Alternatives Considered" for the originally-proposed version and
why it turned out to be unreachable.

For every active `InferenceStep`, for every id in its `premises`: if
that id names another `InferenceStep` (a meta-reasoning citation, not
an ordinary object) and that cited step's own `superseded_by` is set,
emit a WARNING naming the citing step, the cited step, and its
successor. If the premise names an ordinary `KnowledgeObject` (a
`Claim`, etc.) rather than an `InferenceStep`, it's out of scope.

WARNING, not ERROR, for the same reason `InferenceConfidenceConflictConstraint`
is a WARNING: the cited step still exists and is still well-formed —
it's epistemically suspect to still be citing it, not structurally
invalid.

Registered as `"stale_premise"` in `OPTIONAL_CONSTRAINTS_BY_NAME`,
independent of the other four — a structure that uses `InferenceStep`
for simple provenance, or never cites one `InferenceStep`'s id from
another's `premises`, is unaffected.

## 3. Cycle rejection folded into `SupersessionChainConstraint`

A small addition to the existing constraint rather than a new one:
walk each step's `superseded_by` chain (bounded by structure size, to
avoid a runaway loop on already-malformed input) and emit the
existing constraint's ERROR if a step is reachable from itself. This
stays ERROR, matching the rest of `SupersessionChainConstraint` — a
cycle is a structural defect, not a resolvable disagreement, so it
doesn't belong at `stale_premise`'s or `inference_confidence_conflict`'s
WARNING tier.

---

# Non-Goals

- No automatic resolution. `rank_by_entrenchment` ranks; it does not
  write `superseded_by`. `StalePremiseConstraint` flags; it does not
  remove the stale premise or the object it points to. Both extend
  ADR-001's existing non-goal rather than reopening it.
- No change to `InferenceConfidenceConflictConstraint`'s detection
  logic or severity — it already does its job correctly.
- No cross-session or cross-agent resolution policy (who wins when
  two agents' branches disagree) — that belongs to whatever merges
  the branches (`cks-runtime` / `cks-mcp`), not `cks-core`.

---

# Alternatives Considered

## Storing an explicit entrenchment/priority field on `InferenceStep`

Rejected. It would go stale the instant a new competing
`InferenceStep` is added for the same conclusion, requiring the same
synchronization discipline `confidence` + structural order already
give for free via a pure query.

## Auto-superseding the lower-confidence step

Rejected outright, for the same reason ADR-001 already rejected
`cks-core` deriving conclusions itself — confidence alone, without the
`justification` behind it, is too weak a signal to automate, and
doing so silently would remove the "surface for review" property
`inference_confidence_conflict` was built for in the first place.

## Flagging a premise that shares a *conclusion* with a fully-superseded step

This was the originally-proposed version of `StalePremiseConstraint`:
flag a premise id that is the `conclusion` of one or more
`InferenceStep`s, all of which are superseded. Turns out to be
unreachable on valid data and was replaced with the id-citation
version above before implementation was complete. Reason: `SupersessionChainConstraint`
already requires a successor to target the same `conclusion` as the
step it supersedes, so the set of `InferenceStep`s concluding any
given id, restricted to that requirement, always forms a forest —
and a finite forest always has at least one un-superseded leaf. The
only way for *every* step concluding some id to be superseded is a
cycle or a dangling successor, both already separate ERRORs. A
constraint built on that premise would only ever fire alongside an
error that's already reported, making it redundant rather than a new
signal.

## Making `StalePremiseConstraint` an ERROR

Rejected. A stale premise doesn't make the structure invalid the way
a dangling reference does — the referenced object still exists, only
the `InferenceStep` chain that justified relying on it is gone.
Matching `inference_confidence_conflict`'s WARNING tier keeps both
"your reasoning needs review" signals at the same severity.

---

# Consequences

## Positive

- Closes the two concrete gaps left after ADR-001 without touching
  any of its four existing constraints' behavior.
- `rank_by_entrenchment` gives `cks-mcp` something concrete to hand an
  agent resolving an `inference_confidence_conflict` WARNING, instead
  of the agent re-deriving a ranking from raw `confidence` values
  inline each time.
- `StalePremiseConstraint` and the cycle check are pure additions to
  the opt-in reasoning extension — a structure that never adopted
  ADR-001's `InferenceStep` vocabulary, or adopted it without ever
  using `superseded_by`, sees no new diagnostics.
- Complements, rather than depends on, `cks-runtime`'s operation-log
  and merge work (ADR-007 there): two branches independently creating
  disjoint `InferenceStep` objects for the same conclusion merge
  cleanly at the Runtime level (different object ids, not a field
  conflict), and only afterward does `inference_confidence_conflict`
  surface the resulting belief disagreement at validation time — the
  two layers don't need to know about each other.

## Negative

- A fourth and fifth diagnostic type for callers that already parse
  `reasoning.py`'s WARNING/ERROR output to special-case.
- `StalePremiseConstraint` walks premise chains per active step; on a
  structure with many long-lived `InferenceStep`s this is more work
  per `validate_knowledge` call than the existing four constraints,
  though bounded the same way the new cycle check is.

---

# Status

Implemented in cks-core 1.17.0. Depends only on ADR-001's existing
`InferenceStep` vocabulary and constraints; adds no new structural
operator and no change to `core.py`.