# Architecture

This document describes the architecture of the Canonical Knowledge Structure (CKS) Python reference implementation.

The implementation follows the architecture defined by the CKS specifications while remaining completely implementation-independent.

The goal of the reference implementation is not merely to provide a working library, but to demonstrate the canonical behaviour expected from every conforming implementation.

---

# Architectural Overview

The CKS architecture is organised as a layered system.

```text
                    Applications
                          │
                          ▼
          Canonical Knowledge Interface
                    (interface.py)
                          │
                          ▼
                Reference Engine
                  (engine.py)
        ┌────────────┼────────────┐
        ▼            ▼            ▼
 Serialization   Validation    Inspection
serialization.py validator.py   engine.py
        │            │
        │            ▼
        │     Constraint Registry
        │       (constraints/)
        │
        ▼
 Core Semantic Model
      (core.py)

  CLI (Command-Line Interface)
        │
        └── validate, parse, inspect, evolve
```

Each layer has a clearly defined responsibility.

Higher layers never modify lower layers.

---

# Design Principles

The architecture follows five fundamental principles.

## Representation Independence

Knowledge is independent of its representation.

No module assumes that JSON, Python objects, or any storage backend is the primary representation.

---

## Determinism

Every public operation is deterministic.

Identical inputs always produce identical observable outputs.

---

## Observational Purity

Public operations never modify their inputs.

Every operation observes immutable knowledge structures.

---

## Layer Separation

Each module has a single responsibility.

Semantic concepts are isolated from serialization, validation, and public APIs.

---

## Implementation Independence

Every implementation is free to choose its internal algorithms provided that the observable behaviour remains identical.

---

# Core Layer

```
core.py
```

The Core layer defines the immutable semantic model.

It contains the fundamental concepts introduced in the CKS specifications:

* ObjectIdentity
* KnowledgeObject
* CanonicalRelation
* KnowledgeStructure

Every other module depends on this layer.

The Core layer has no knowledge of:

* JSON;
* validation;
* diagnostics;
* engines;
* APIs.

It only defines canonical semantic objects.

---

# Serialization Layer

```
serialization.py
```

The Serialization layer converts between canonical JSON and the semantic model.

Responsibilities include:

* parsing canonical JSON;
* serializing Knowledge Structures;
* enforcing serialization rules;
* preserving round-trip equivalence.

The serializer never performs semantic validation.

---

# Validation Layer

```
validator.py
```

The Validator implements the canonical validation pipeline.

The pipeline consists of three stages:

```text
Structural Validation
          │
          ▼
Semantic Validation
          │
          ▼
Constraint Evaluation
```

Each stage is independent.

Diagnostics produced by every stage are merged into a single ValidationResult.

---

# Constraint Registry

The validation layer includes a constraint registry.

The registry allows implementations to register additional deterministic validation constraints.

Constraints are organized into **Validation Domains** (CKS‑005):

- `structural.py` — unique identity, referential integrity.
- `semantic.py` — derivation arity, cycle detection.
- `contradiction.py` — hard, ERROR‑severity contradictions between facts.
- `reasoning.py` — belief revision: `InferenceStep` integrity, confidence bounds, supersession chains, stale‑premise citations, and the inference‑conflict WARNING (see "Belief Revision" below).
- `temporal.py` — `TemporalValidityConstraint` (ADR‑003): flags objects whose `valid_until` has passed.
- `layering.py` — `LayeringRuleConstraint` (ADR‑004): enforces the ecosystem's `cks-core < cks-runtime < cks-mcp` dependency direction.
- `ontology.py`, `projection.py`, `verification.py` — additional opt‑in domains for ontology-, projection-, and verification-specific checks.
- `builtin.py` — manifest that instantiates and exports all built‑in and optional constraints.

Constraints execute after structural and semantic validation.

Built‑in constraints are auto‑registered. Optional constraints,
such as `EmbeddingProjectionIntegrityConstraint`, `temporal_validity`, and
`layering_rule`, are not registered by default and must be opted‑in
explicitly per validator instance or process‑wide (see the Plugin
Development Guide).

---

# Belief Revision & Reasoning

```
constraints/reasoning.py
```

Alongside plain facts, a Knowledge Structure can record `InferenceStep`
objects — a conclusion, the premises it was drawn from, an operator, a
confidence score, and an optional justification. This lets CKS represent
not just what is known but *why*, and reason about disagreements between
inference paths that reach the same conclusion.

The reasoning domain provides:

- **Constraints** — `InferenceReferentialIntegrityConstraint`,
  `ConfidenceBoundsConstraint`, `SupersessionChainConstraint` (rejects
  `superseded_by` cycles), `InferenceConfidenceConflictConstraint`
  (WARNING — active steps sharing a conclusion but disagreeing on
  confidence), `StalePremiseConstraint` (WARNING — a premise citing an
  already-superseded step).
- **Pure queries** — `rank_by_entrenchment()` ranks competing steps by
  confidence; `explain_inference()` walks a conclusion's inference chain
  back to base facts.
- **Evolution operators** — `RecordInference` appends a new step;
  `ResolveInferenceConflict` atomically supersedes every losing step once
  a winner has been chosen.

None of these mutate a structure except the two evolution operators,
which follow the same observational-purity guarantees as the rest of
`evolution.py`. See ADR‑001 and ADR‑002 for the design rationale.

---

# Evolution Engine

```
evolution.py
```

The Evolution Engine implements CKS‑004 (Canonical Structure Evolution).

It provides:

- `StructuralOperator` — abstract base class for admissible transformations.
- `OperatorContract` — formal contract specifying preconditions, postconditions, and invariants.
- Genesis operators: `AddObject`, `AddRelation`, `RecordInference`.
- Decay operators: `RemoveObject`, `RemoveRelation`.
- Mutation operators: `UpdateObject` (merge and replace modes), `RenameObject`, `ResolveInferenceConflict`.
- `compose()` — apply a sequence of operators in order.
- `merge()` — three‑way merge (base/branch/branch) with conflict detection and optional per‑identity `resolutions`.
- `query_subgraph()` — k‑hop subgraph extraction with optional budget and type‑weighted ranking.

All operators are observationally pure and preserve structural invariants.
Every operator also exposes documented, read‑only properties (`.obj`,
`.object_id`, `.relation_id`, `.structure_patch`, `.mode`, `.new_name`) for
safe introspection without reaching into private state.

---

# Import / Export Layer

```
adapters/
```

The adapters package converts between canonical structures and external
RDF‑family formats, independent of the core semantic model:

- `jsonld_to_cks.py` / `cks_to_jsonld.py` — JSON‑LD.
- `rdf_to_cks.py` / `cks_to_rdf.py` — Turtle and RDF/XML.

These are driven by the `cks convert` and `cks export` CLI commands. The
RDF/XML reader rejects any DOCTYPE declaration to prevent entity‑expansion
("billion laughs") attacks.

---

# Format Versioning

```
serialization.py, cli/commands/migrate.py
```

Every serialized structure carries `_cks_format_version`,
`_cks_min_reader_version`, and `_cks_metadata`. `parse()` checks the
installed `cks-core` version against a file's minimum reader requirement
and raises `FormatVersionError` on mismatch. `is_legacy_format()` detects
files written before this scheme (pre‑1.15.0); `cks migrate` re‑serializes
them into the current format (`--in-place`, `--check`).

---

# Reference Engine

```
engine.py
```

The Reference Engine coordinates all canonical operations.

It provides a single implementation-independent interface for:

* construction;
* serialization;
* validation;
* comparison;
* inspection;
* extraction;
* projection;
* evolution.

The engine delegates specialised work to the appropriate modules.

It contains very little domain-specific logic itself.

---

# Public Interface

```
interface.py
```

The public interface exposes the canonical API defined by CKS-007.

Applications are expected to import functions from this module.

Typical usage:

```python
from cks import parse
from cks import validate
from cks import serialize
```

The interface hides implementation details while exposing deterministic canonical behaviour.

---

# Diagnostics

Diagnostics are represented independently of validation.

```
diagnostics.py
```

defines:

* Diagnostic
* DiagnosticSeverity
* DiagnosticCollection

Validation produces diagnostics but does not own their implementation.

This separation allows diagnostics to evolve independently.

---

# Validation Results

```
result.py
```

Validation outcomes are represented using ValidationResult.

A ValidationResult contains:

* validity;
* diagnostics;
* evaluated constraints;
* metadata.

The result object is immutable.

---

# Module Dependencies

The implementation follows a directed dependency graph.

```text
core
 │
 ├────────────┐
 ▼            ▼
serialization validator
      │        │
      └────┬───┘
           ▼
        engine
           │
           ▼
       interface
           │
           ▼
          cli
```

Evolution (`evolution.py`) depends on core and is used by engine.

Dependencies always point toward higher abstraction layers.

Circular dependencies are intentionally avoided.

---

# Typical Execution Flow

The following sequence illustrates a typical validation operation.

```text
Application
      │
      ▼
validate()
      │
      ▼
Reference Engine
      │
      ▼
Validator
      │
      ├── Structural Validation
      ├── Semantic Validation
      └── Constraint Evaluation
      │
      ▼
ValidationResult
```

Each step is deterministic and observationally pure.

---

# Repository Structure

The Python reference implementation is organised as follows.

```text
src/
└── cks/
    ├── __init__.py
    ├── _version.py
    ├── interface.py
    ├── engine.py
    ├── core.py
    ├── serialization.py
    ├── validation.py
    ├── validator.py
    ├── diagnostics.py
    ├── result.py
    ├── evolution.py
    ├── plugin.py
    ├── schema.py
    ├── schemas/
    ├── adapters/
    │   ├── jsonld_to_cks.py
    │   ├── cks_to_jsonld.py
    │   ├── rdf_to_cks.py
    │   └── cks_to_rdf.py
    ├── cli/
    │   ├── __init__.py
    │   ├── formatters.py
    │   └── commands/
    │       ├── validate.py
    │       ├── parse.py
    │       ├── inspect.py
    │       ├── evolve.py
    │       ├── convert.py
    │       ├── export.py
    │       ├── migrate.py
    │       ├── plugin.py
    │       └── schema.py
    └── constraints/
        ├── __init__.py
        ├── base.py
        ├── builtin.py
        ├── registry.py
        ├── structural.py
        ├── semantic.py
        ├── contradiction.py
        ├── reasoning.py
        ├── temporal.py
        ├── layering.py
        ├── ontology.py
        ├── projection.py
        └── verification.py

docs/
examples/
    corpus/
        valid_theory_example.json
        invalid_duplicate_id.json
        invalid_dangling_reference.json
        invalid_derivation_cycle.json
tests/
```

---

# Extensibility

The architecture is intentionally modular.

Delivered through this extension model: the belief‑revision/reasoning
domain, the temporal‑validity and layering‑rule optional constraints, the
RDF‑family import/export adapters, and format versioning — none of which
required changes to the Core layer's semantic model.

Future versions may introduce additional components such as:

- semantic reasoning tools (pathfinding, concept similarity) beyond belief revision;
- alternative serialization formats;
- optimisation engines;
- additional language bindings;
- CLI extensions.

These extensions should integrate through the existing canonical interfaces without modifying the semantic model.

---

# Summary

The CKS architecture separates semantic concepts from implementation details.

Every layer has a single responsibility, and every public operation preserves the canonical guarantees defined by the CKS specifications:

* representation independence;
* determinism;
* observational purity;
* implementation independence.

The next document, **API Reference**, describes the complete public interface exposed by the Python reference implementation.
