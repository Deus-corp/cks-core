# Introduction

## Purpose

The purpose of this specification is to define the Python Reference
Implementation of the Canonical Knowledge Structure Validator and
Reference Engine.

This document provides:

- a normative specification of the public Python API;
- an informative description of internal algorithms;
- a mapping from the abstract components defined in CKS‑006 to
  concrete Python modules and classes;
- the minimum test criteria that any conformant Python implementation
  shall satisfy.

## Relationship to Core Specifications

This implementation realises the canonical validation model defined in
CKS‑005 and the Reference Engine architecture defined in CKS‑006.  It
exposes the Canonical Knowledge Interface defined in CKS‑007 through
Python language bindings.

## Normative Status

The public API, observable behaviour, and conformance criteria defined
in this document are normative.  Internal algorithms are informative:
alternative implementations may use different internal strategies
provided they preserve identical observable behaviour.

## Document Conventions

Python code fragments are presented in monospaced type.  Class and
function signatures specify types using Python 3.12+ syntax.  The
package name `cks` is reserved for the reference implementation.

---

# Reference Binding Principles

## Purpose

The Python Reference Binding provides the first normative realization of the Canonical Knowledge Interface.

It establishes the observable behaviour against which future language bindings may be compared.

The Python Reference Binding therefore serves as the behavioural reference implementation of the Canonical Knowledge Structure ecosystem.

---

## Binding Principle

The Python Reference Binding preserves:

- canonical semantics;
- canonical operation contracts;
- canonical object identity;
- deterministic behaviour;
- implementation independence.

Python syntax represents canonical interaction.

It does not redefine canonical interaction.

---

## Observable Behaviour

Only observable behaviour is normative.

Observable behaviour includes:

- public API;
- operation contracts;
- canonical object identity;
- validation results;
- diagnostics;
- deterministic execution.

Internal implementation strategies remain implementation-specific.

---

## Relationship to Future Bindings

Future bindings for Rust,

Java,

Go,

C++,

or other implementation languages

shall preserve the observable behaviour established by this Reference Binding.

Equivalent observable behaviour,

rather than implementation language,

constitutes canonical equivalence.

---

# Architectural Mapping

## Component Correspondence

The abstract components defined in CKS‑006, Section 4 are realised by
the following Python modules and classes.

| Abstract Component (CKS‑006) | Python Realisation |
|------------------------------|-------------------|
| Loader | `cks.interface.load()` |
| Deserializer | `cks.serialization.deserialize()` |
| Structural Validator | `cks.validator.structural_validate()` |
| Semantic Validator | `cks.validator.semantic_validate()` |
| Constraint Evaluator | `cks.validator.evaluate_constraints()` |
| Diagnostic Engine | `cks.diagnostics.Diagnostic` |
| Validation Result Generator | `cks.result.ValidationResult` |
| Validator (CKS‑005) | `cks.validator.validate()` |
| Reference Engine (CKS‑006) | `cks.engine.ReferenceEngine` |

## Package Structure

The Python package `cks` is organised into the following modules:

- `cks/__init__.py` — package initialisation.
- `cks/core.py` — KnowledgeStructure, KnowledgeObject, CanonicalRelation classes.
- `cks/serialization.py` — JSON deserialization and serialization.
- `cks/validator.py` — Validation pipeline and constraint evaluation.
- `cks/diagnostics.py` — Diagnostic and DiagnosticCollection classes.
- `cks/result.py` — ValidationResult class.
- `cks/engine.py` — ReferenceEngine orchestrator.
- `cks/interface.py` — Public API functions (validate, parse, serialize).
- `cks/constraints/` — Canonical validation constraint definitions:
  - `__init__.py`
  - `identity.py`
  - `structure.py`
  - `relations.py`
  - `derivations.py`

---

## Module Independence

Individual Python modules represent logical realizations of canonical responsibilities.

Alternative implementations may reorganize internal module boundaries provided they preserve:

- public API;
- observable behaviour;
- canonical operation contracts;
- canonical semantics.

Module organisation is therefore informative rather than normative.

---

# Public API

## Canonical Knowledge Objects

### KnowledgeStructure

```python
class KnowledgeStructure:
    """A Canonical Knowledge Structure as defined in CKS‑001, Section 9."""

    def __init__(self, objects: list[KnowledgeObject]):
        """Construct a KnowledgeStructure from a list of KnowledgeObjects.

        Preconditions:
            - Every object in `objects` has a unique canonical identity.
        Raises:
            ValueError: if duplicate identities are detected.
        """
        ...

    @property
    def objects(self) -> list[KnowledgeObject]:
        """Return the list of all KnowledgeObjects in this structure."""
        ...

    def relations(self) -> list[CanonicalRelation]:
        """Return all CanonicalRelations contained in this structure."""
        ...

    def get(self, identity: str) -> KnowledgeObject | None:
        """Return the KnowledgeObject with the given canonical identity,
        or None if no such object exists."""
        ...
```

### KnowledgeObject

```python
@dataclass(frozen=True)
class KnowledgeObject:
    """A Knowledge Object as defined in CKS‑001, Sections 1–2."""

    identity: ObjectIdentity
    structure: ObjectStructure
```

### ObjectIdentity

```python
@dataclass(frozen=True)
class ObjectIdentity:
    """Canonical identity as defined in CKS‑001, Section 2.2."""

    id: str       # globally unique canonical identifier
    type: str     # canonical object type
    name: str     # canonical human-readable designation
```

### CanonicalRelation

```python
class CanonicalRelation(KnowledgeObject):
    """A Canonical Relation as defined in CKS‑001, Section 8."""

    @property
    def participants(self) -> list[str]:
        """Return the canonical identities of participating KnowledgeObjects."""
        ...

    @property
    def relation_type(self) -> str:
        """Return the semantic type of this relation."""
        ...
```

## Validation

### validate

```python
def validate(structure: KnowledgeStructure) -> ValidationResult:
    """Validate a Canonical Knowledge Structure.

    This function is the canonical realisation of CKS‑005.

    Preconditions:
        - structure is a well-formed KnowledgeStructure.
    Postconditions:
        - Returns a ValidationResult that faithfully represents the
          canonical validity of the input structure.
        - The input structure is not modified.
    Raises:
        TypeError: if structure is not a KnowledgeStructure.
    """
    ...
```

### ValidationResult

```python
@dataclass(frozen=True)
class ValidationResult:
    """Canonical validation outcome as defined in CKS‑005, Section 7."""

    is_valid: bool
    diagnostics: DiagnosticCollection
    evaluated_constraints: list[str]
    metadata: dict[str, object]
```

## OperationContext

```python
@dataclass(frozen=True)
class OperationContext:
    """Implementation-independent execution context."""

    operation: str
    version: str
    metadata: dict[str, object]
```

The OperationContext provides execution metadata without modifying canonical semantics.

### Diagnostic

```python
@dataclass(frozen=True)
class Diagnostic:
    """A canonical diagnostic as defined in CKS‑006, Section 8."""

    identity: str               # canonical diagnostic identifier
    severity: DiagnosticSeverity
    message: str
    location: str | None        # canonical identity of the affected entity
    metadata: dict[str, object]
```

### DiagnosticSeverity

```python
class DiagnosticSeverity(Enum):
    INFORMATION = "information"
    WARNING = "warning"
    ERROR = "error"
```

## Serialization

### parse

```python
def parse(source: str | dict) -> KnowledgeStructure:
    """Parse a serialized representation into a KnowledgeStructure.

    Preconditions:
        - source is a valid JSON string or a dict conforming to the
          canonical serialization model (CKS‑003).
    Postconditions:
        - Returns a KnowledgeStructure semantically equivalent to the
          serialized representation.
    Raises:
        SerializationError: if source cannot be parsed.
    """
    ...
```

### serialize

```python
def serialize(structure: KnowledgeStructure) -> str:
    """Serialize a KnowledgeStructure to its canonical JSON representation.

    Postconditions:
        - parse(serialize(S)) ≡ S (structural equivalence, CKS‑001, Section 15).
    """
    ...
```

## Engine Access

```python
class ReferenceEngine:
    """Reference Engine as defined in CKS-006."""

    def construct(...): ...
    def parse(...): ...
    def validate(...): ...
    def diagnose(...): ...
    def inspect(...): ...
    def serialize(...): ...
    def compare(...): ...
    def extract(...): ...
    def project(...): ...
    def evolve(...): ...
```

---

# Canonical Exceptions

The Python Reference Binding defines the following canonical exception hierarchy.

```python
class CKSError(Exception):
    """Base class for all canonical exceptions."""
```

---

```python
class SerializationError(CKSError):
    """Raised when canonical serialization cannot be parsed or produced."""
```

---

```python
class ValidationError(CKSError):
    """Raised when validation cannot be completed."""
```

---

```python
class InterfaceError(CKSError):
    """Raised when canonical interface contracts are violated."""
```

---

```python
class ConformanceError(CKSError):
    """Raised when implementation conformance cannot be established."""
```

All canonical exceptions preserve implementation-independent semantics.

---

# Internal Algorithms (Informative)

## Deserialization from JSON

The canonical JSON format represents a KnowledgeStructure as an object
with a single key "objects" mapping to an array of KnowledgeObject
representations.  Each object representation contains "identity"
(id, type, name) and "structure" (content, relations,
metadata).

The deserializer reconstructs Python objects from this representation
and verifies the uniqueness of canonical identities.  Duplicate
identities raise a SerializationError.

## Structural Validation

Structural validation verifies:

- Every object has a unique canonical identity.
- Every CanonicalRelation references only existing objects.
- Referential integrity holds (no dangling references).

## Semantic Validation

Semantic validation verifies constraints on relations and derivations
as specified in CKS‑001, Sections 8 and 16.  The current reference
implementation performs a graph reachability check for derivation
chains.

## Constraint Evaluation

Each canonical validation constraint (CKS‑005, Section 5) is
represented by a callable object in the cks.constraints module.
The validator iterates over all applicable constraints, evaluates each
independently, and collects diagnostics for any violations.

---

# Test Suite (Minimum Criteria)

A conformant Python implementation shall pass the following minimum
tests:

Test Description
- T1 parse correctly deserializes a minimal valid KnowledgeStructure.
- T2 serialize followed by parse is structurally equivalent to the original.
- T3 validate returns is_valid=True for a valid structure with no violations.
- T4 validate returns is_valid=False for a structure with a missing required object.
- T5 validate returns is_valid=False for a structure with a dangling reference.
- T6 validate returns is_valid=False for a structure with a duplicate identity.
- T7 Repeated calls to validate on identical input produce identical output (determinism).
- T8 validate does not modify the input structure (observational purity).
- T9Equivalent canonical inputs shall produce canonically equivalent observable outputs. The implementation shall preserve Semantic Conformance and Behavioural Conformance as defined in CKS-008.

The complete test suite, including edge‑case and regression tests, is
maintained in the tests/ directory of the reference implementation
repository.

---

# Conformance Criteria

A Python implementation conforms to this specification if and only if:

- (C1) It exposes the public API defined in Section 3 with the
  specified signatures and observable behaviour.
- (C2) It passes all tests defined in Section 5.
- (C3) It satisfies the Validator Conformance criteria defined in
  CKS‑008, Section 3.
- (C4) It satisfies the Reference Engine Conformance criteria
  defined in CKS‑008, Section 4.
- (C5) It satisfies the CKI Conformance criteria defined in
  CKS‑008, Section 5.

---

# Future Extensions

The Python Reference Implementation may be extended with:

- additional serialization formats (YAML, binary),
- performance optimisations (parallel constraint evaluation),
- developer tooling (diagnostic formatters, structure visualisation),
- integration with the CKI over network protocols.

All extensions shall preserve the normative public API and observable
behaviour defined in this specification.

The Python Reference Binding serves as the behavioural reference for future conformant language bindings.

Future bindings shall remain observationally equivalent to this Reference Binding while preserving complete implementation independence.

Accordingly,

Python is the first canonical behavioural reference,

not the canonical implementation language.

---

# Mathematical Interpretation

The Python Reference Binding constitutes the first executable realization of the Canonical Knowledge Interface.

Its purpose is not to define canonical computation,

but to demonstrate that the canonical computational model established by the CKS Core Specifications is fully realizable within a concrete programming language.

Future bindings preserve the same canonical semantics while adopting different implementation technologies.

The Python Reference Binding therefore serves as the behavioural reference implementation of the Canonical Knowledge Structure ecosystem.