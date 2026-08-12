# Canonical Knowledge Structure (CKS)

> A universal, representation-independent foundation for knowledge.

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-400%20passed-brightgreen)
![Version](https://img.shields.io/badge/version-1.21.1-blue)
[![PyPI](https://img.shields.io/pypi/v/cks-core)](https://pypi.org/project/cks-core/)

CKS is an open specification that defines how knowledge can be represented,
validated, exchanged, and evolved independently of programming languages,
document formats, databases, or AI systems.

Rather than introducing yet another serialization format or programming
language, CKS defines a **canonical semantic layer** shared by humans,
software, and artificial intelligence.

---

# Ecosystem

CKS Core is the semantic foundation of the CKS ecosystem.
Other projects build upon it:

| Project | Description | Repository |
|---------|-------------|------------|
| **cks-core** | Canonical semantic engine – the single source of canonical truth. | [Deus-corp/cks-core](https://github.com/Deus-corp/cks-core) |
| **cks-runtime** | Operational environment – sessions, transactions, persistence. | [Deus-corp/cks-runtime](https://github.com/Deus-corp/cks-runtime) |
| **cks-mcp** | MCP server – exposes CKS to LLMs and autonomous agents. | [Deus-corp/cks-mcp](https://github.com/Deus-corp/cks-mcp) |
| **cks-studio** | Visual workspace – explore, monitor, and manage graphs. | [Deus-corp/cks-studio](https://github.com/Deus-corp/cks-studio) |
| **cks-website** | Documentation & demo site. | [Deus-corp/cks-website](https://github.com/Deus-corp/cks-website) |

---

# Why CKS?

Today the same knowledge exists simultaneously in many incompatible forms:

- documents
- databases
- JSON
- XML
- source code
- knowledge graphs
- ontologies
- AI prompts
- APIs

Each representation describes the same underlying knowledge differently.

CKS separates **knowledge itself** from every concrete representation.

```
Knowledge
      │
      ▼
Canonical Knowledge Structure (CKS)
      │
 ┌────┼───────────────┐
 ▼    ▼               ▼
JSON Python Database Natural Language
```

Representations may change.

Canonical knowledge remains the same.

---

# Core Principles

CKS is founded on four simple principles.

### Knowledge exists independently of its representation.

Knowledge is not JSON.

Knowledge is not a PDF.

Knowledge is not source code.

Representations are temporary.

Knowledge is not.

---

### Structure preserves meaning.

Meaning is preserved by canonical structure rather than by syntax.

---

### Representation preserves structure.

Different representations may express the same canonical structure.

---

### Canonical operations belong to knowledge itself.

Validation.

Serialization.

Comparison.

Evolution.

Inspection.

These are operations on knowledge—not on files, databases, or programming
languages.

---

# Architecture

The CKS ecosystem consists of implementation-independent specifications.

| Specification | Purpose |
|--------------|---------|
| CKS-000 | Foundations and terminology |
| CKS-001 | Canonical semantic model |
| CKS-002 | Knowledge construction |
| CKS-003 | Canonical serialization |
| CKS-004 | Structure evolution |
| CKS-005 | Validation |
| CKS-006 | Reference Engine |
| CKS-007 | Canonical Knowledge Interface |
| CKS-008 | Conformance |
| CKS-009 | Reference Knowledge Corpus |
| CKS-B001 | Python Reference Implementation |

---

# Features

The current Python reference implementation provides:

- Immutable Canonical Knowledge Objects
- Canonical Relations
- Immutable Knowledge Structures
- Canonical JSON Serialization
- Deterministic Validation Pipeline
- Diagnostic System
- Reference Engine
- Canonical Public API
- Structural Comparison
- Projection
- Extraction
- Inspection
- Conformance Test Suite
- Command-Line Interface (validate, parse, inspect, evolve, schema, plugin)
- Structural Evolution (Genesis/Decay operators)
- Configurable Severity Thresholds
- HTML and Markdown Report Formatters
- Batch Validation (multiple files)
- JSON‑LD, Turtle, RDF/XML Import (via `cks convert`)
- JSON‑LD, Turtle, RDF/XML Export (via `cks export`)
- Strict Plugin Validation (`--strict`)
- Static Type Checking (mypy)
- Optional Extension Constraints (opt‑in validators for specialised knowledge types)
- Merkle‑tree based structural hashing for O(1) comparison and diff computation
- Three‑way merge (base‑branch‑branch) with conflict detection and structured error reporting
- In‑place object updates via `UpdateObject` (merge and replace modes)
- **`RenameObject` operator** — changes an object's `identity.name` without invalidating relations or cascading deletions
- **Public operator properties** — safe, documented introspection of structural operators (`.obj`, `.object_id`, `.relation_id`, `.structure_patch`, `.mode`, `.new_name`)
- k‑hop subgraph extraction (`query_subgraph`) with optional budget and type‑weighted ranking
- Partial three‑way merge with per‑identity conflict resolution (`resolutions` parameter)
- Format versioning (`_cks_format_version` / `_cks_min_reader_version`) and `cks migrate` for legacy files
- Constraint entry points — third‑party packages register custom constraints via `cks.constraints` in `pyproject.toml`

### Belief Revision & Reasoning

CKS can represent not just facts but the *inferences* drawn from them, and reason about conflicts between those inferences (see ADR‑001, ADR‑002):

- **`InferenceStep`** objects — record a conclusion, its premises, an operator, a confidence score, and an optional justification
- **`RecordInference`** evolution operator — appends a new `InferenceStep` to a structure
- **`InferenceConfidenceConflictConstraint`** — flags active inference steps that share a conclusion but disagree on confidence (WARNING, not ERROR — a resolvable belief conflict, not a structural error)
- **`StalePremiseConstraint`** — flags an active step citing a premise that has itself been superseded
- **`SupersessionChainConstraint`** — validates `superseded_by` chains and rejects cycles
- **`rank_by_entrenchment`** — ranks competing inference steps by confidence
- **`explain_inference`** — walks a conclusion's inference chain back to base facts, reporting operator, confidence, justification, and supersession history per step
- **`ResolveInferenceConflict`** operator — the write‑side counterpart: given a conclusion and a chosen winner, atomically supersedes every other active step reaching that conclusion

This is the reasoning substrate that `cks-mcp`'s conflict‑resolution tools are built on.

### Optional Extension Constraints

Opt‑in validators for specialised knowledge types, registered via `cks.constraints.builtin.OPTIONAL_CONSTRAINTS_BY_NAME`:

- **`temporal_validity`** (ADR‑003) — flags objects whose `structure.valid_until` has passed
- **`layering_rule`** (ADR‑004) — enforces the CKS ecosystem's dependency direction (`cks-core < cks-runtime < cks-mcp`) on `depends_on` relations

---

# Design Goals

CKS is designed to be:

- deterministic
- immutable
- observationally pure
- representation-independent
- implementation-independent
- language-independent
- suitable for formal verification

---

# Current Repository

This repository contains the official Python Reference Implementation of
the Canonical Knowledge Structure specifications.

Currently implemented:

- ✅ Canonical Knowledge Objects
- ✅ Canonical Relations
- ✅ Canonical Knowledge Structures
- ✅ Canonical Serialization
- ✅ Validation Pipeline
- ✅ Diagnostic System
- ✅ Reference Engine
- ✅ Canonical Public Interface
- ✅ Command-Line Interface
- ✅ Structural Evolution (CKS‑004)
- ✅ Reference Knowledge Corpus
- ✅ Conformance Test Suite (400+ tests)
- ✅ PyPI Publication
- ✅ Import/Export Adapters (JSON‑LD, Turtle, RDF/XML)
- ✅ Modular CLI (commands refactored into separate handlers)
- ✅ Contract Documentation (`docs/contracts.md`)
- ✅ Static Type Checking (mypy)
- ✅ Format Versioning & `cks migrate`
- ✅ Constraint Entry Points (third‑party plugin registration)
- ✅ Belief Revision & Reasoning Engine (`InferenceStep`, conflict detection, `explain_inference`)
- ✅ Temporal Validity & Layering Rule extension constraints

Planned:

- Additional language implementations (Rust, TypeScript)

---

# Installation

From PyPI:

```bash
pip install cks-core
```

Or from source:

```bash
git clone https://github.com/Deus-corp/cks-core.git
cd cks-core
pip install -e .
```

---

# Quick Example

```python
from cks import (
    construct,
    validate,
    serialize,
)

from cks.core import (
    KnowledgeObject,
    ObjectIdentity,
)

obj = KnowledgeObject(
    identity=ObjectIdentity(
        id="obj-1",
        type="Definition",
        name="Knowledge",
    )
)

structure = construct([obj])

result = validate(structure)

print(result.is_valid)

print(serialize(structure))
```

Or use the command line:

```bash
# Validate a knowledge structure
cks validate examples/corpus/valid_theory_example.json

# Evolve a structure by adding an object
cks evolve examples/corpus/valid_theory_example.json examples/corpus/evolve_add.json
```

```bash
# Three-way merge of diverged structures
from cks import merge, MergeConflictError

base = construct([obj1, obj2])
branch_a = construct([obj1, obj3])
branch_b = construct([obj2, obj4])

try:
    merged = merge(base, branch_a, branch_b)
except MergeConflictError as e:
    for conflict in e.conflicts:
        print(f"Conflict on {conflict.object_id}")

# Partial three-way merge with conflict resolution
base = construct([obj1, obj2])
branch_a = construct([obj1, obj3])
branch_b = construct([obj2, obj4])

try:
    merged = merge(base, branch_a, branch_b, resolutions={"obj-1": "branch_a"})
except MergeConflictError as e:
    for conflict in e.conflicts:
        print(f"Unresolved conflict on {conflict.object_id}")
```

Or convert between formats:

```bash
# Convert JSON‑LD to CKS
cks convert examples/corpus/person.jsonld --format json-ld --output person.cks.json

# Export CKS to Turtle
cks export examples/corpus/valid_theory_example.json --format turtle --output theory.ttl
```

---

# Testing

Run the complete conformance suite:

```bash
python -m pytest -v
```

Current status:

- 400+ tests
- all passing

The test suite verifies:

- deterministic behaviour
- immutability
- observational purity
- canonical serialization
- validation correctness
- public API conformance
- structural equivalence

---

# Documentation

The complete specification is published separately.

Core specifications:

- CKS-000 — Foundations
- CKS-001 — Core Specification
- CKS-002 — Construction
- CKS-003 — Serialization
- CKS-004 — Evolution
- CKS-005 — Validator
- CKS-006 — Reference Engine
- CKS-007 — Canonical Knowledge Interface
- CKS-008 — Conformance

DOI:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21332624.svg)](https://doi.org/10.5281/zenodo.21332624)

---

# Project Status

Current implementation status:

| Component | Status |
|----------|--------|
| Core Model | ✅ Complete |
| Serialization | ✅ Complete |
| Validation | ✅ Complete |
| Reference Engine | ✅ Complete |
| Public API | ✅ Complete |
| Test Suite | ✅ Passing |
| CLI | ✅ Complete |
| Structural Evolution | ✅ Complete |
| Advanced Validation | ✅ Complete |
| Import/Export Adapters | ✅ Complete |
| Modular CLI | ✅ Complete |
| Contract Documentation | ✅ Complete |
| Static Type Checking | ✅ Complete |
| Optional Constraints | ✅ Complete |
| Merkle Hashing & Diff | ✅ Complete |
| Three‑Way Merge | ✅ Complete |
| Query Subgraph | ✅ Complete |
| RenameObject Operator | ✅ Complete |
| Public Operator Properties | ✅ Complete |
| Partial Merge (Resolutions) | ✅ Complete |
| Format Versioning & Migration | ✅ Complete |
| Constraint Entry Points | ✅ Complete |
| Belief Revision & Reasoning Engine | ✅ Complete |
| Temporal Validity Constraint | ✅ Complete |
| Layering Rule Constraint | ✅ Complete |

The current implementation serves as the reference implementation of the
existing CKS specifications.

Future work focuses primarily on expanding the specification rather than
redesigning the implemented components.

---

# Vision

CKS aims to establish a universal semantic foundation for knowledge
exchange between:

- humans
- software
- databases
- distributed systems
- artificial intelligence

through a single canonical representation of knowledge that is independent
of every concrete implementation.

---

# License

MIT