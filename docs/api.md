# API Reference

This document describes the public API exposed by the Canonical Knowledge Structure (CKS) Python reference implementation.

Applications should use the functions documented here instead of importing implementation modules directly.

The public API is defined by the Canonical Knowledge Interface (CKS-007).

---

# Importing CKS

The recommended import style is:

```python
from cks import (
    construct,
    parse,
    serialize,
    validate,
    validate_all,
    diagnose,
    inspect,
    compare,
    extract,
    project,
    evolve,
    merge,
    MergeConflictError,
)

from cks.evolution import (
    AddObject,
    AddRelation,
    RemoveObject,
    RemoveRelation,
    compose,
)
```

All public operations are:

* deterministic;
* observationally pure;
* implementation-independent.

---

# Construction

## construct()

Construct a canonical Knowledge Structure from an iterable of Knowledge Objects.

### Signature

```python
construct(
    objects: Iterable[KnowledgeObject],
) -> KnowledgeStructure
```

### Example

```python
structure = construct(
    [
        object1,
        object2,
        relation,
    ]
)
```

---

# Serialization

## parse()

Parse canonical JSON into a Knowledge Structure.

### Signature

```python
parse(
    source: str | dict,
) -> KnowledgeStructure
```

### Parameters

| Parameter | Description                                  |
| --------- | -------------------------------------------- |
| source    | Canonical JSON string or decoded JSON object |

### Example

```python
structure = parse(json_text)
```

---

## serialize()

Serialize a Knowledge Structure into canonical JSON.

### Signature

```python
serialize(
    structure: KnowledgeStructure,
) -> str
```

### Example

```python
json_text = serialize(structure)
```

The reference implementation guarantees canonical round-trip behaviour.

---

# Validation

## validate()

Execute the complete canonical validation pipeline.

### Signature

```python
validate(
    structure: KnowledgeStructure,
    *,
    min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
) -> ValidationResult
```

### Validation Stages

1. Structural Validation
2. Semantic Validation
3. Constraint Evaluation

### Example

```python
result = validate(structure)

print(result.is_valid)
```

---

## validate_all()

Validate multiple Knowledge Structures and return individual results.

### Signature

```python
validate_all(
    structures: Iterable[KnowledgeStructure],
    *,
    min_severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
) -> list[ValidationResult]
```

### Example

```python
results = validate_all(
    [
        structure1,
        structure2,
    ],
    min_severity=DiagnosticSeverity.WARNING,
)
```

---

## diagnose()

Return diagnostics without exposing the complete ValidationResult.

### Signature

```python
diagnose(
    structure: KnowledgeStructure,
) -> DiagnosticCollection
```

### Example

```python
diagnostics = diagnose(structure)
```

---

# Inspection

## inspect()

Return an implementation-independent summary of a Knowledge Structure.

### Signature

```python
inspect(
    structure: KnowledgeStructure,
) -> Mapping[str, object]
```

### Example

```python
summary = inspect(structure)
```

Typical summary information includes:

* object count;
* relation count;
* structural metadata.

---

# Comparison

## compare()

Compare two Knowledge Structures.

### Signature

```python
compare(
    left: KnowledgeStructure,
    right: KnowledgeStructure,
) -> Mapping[str, object]
```

### Example

```python
comparison = compare(
    structure1,
    structure2,
)
```

The comparison is based on observable structure rather than implementation details.

---

# Extraction

## extract()

Extract a single Knowledge Object.

### Signature

```python
extract(
    structure: KnowledgeStructure,
    identity: str,
) -> KnowledgeObject | None
```

### Example

```python
obj = extract(
    structure,
    "definition-001",
)
```

Returns `None` when the requested object does not exist.

---

# Projection

## project()

Create a new Knowledge Structure containing only selected objects.

### Signature

```python
project(
    structure: KnowledgeStructure,
    identities: Iterable[str],
) -> KnowledgeStructure
```

### Example

```python
subset = project(
    structure,
    [
        "definition-001",
        "theorem-003",
    ],
)
```

Projection never modifies the original structure.

---

# Extension Constraints

CKS provides optional constraints that are not active by default.
They can be registered explicitly to extend the validation pipeline
with domain‑specific rules.

For example, the `EmbeddingProjectionIntegrityConstraint` (available
in `cks.constraints.projection`) enforces that an `EmbeddingProjection`
object points to a valid source object and references its vector
payload externally.

To activate an optional constraint, register it in the global registry
or in a scoped `ConstraintRegistry`:

```python
from cks.constraints.builtin import OPTIONAL_CONSTRAINTS
from cks.constraints.registry import registry

for constraint in OPTIONAL_CONSTRAINTS:
    registry.register(constraint)
```

See the Plugin Development Guide for more details.

---

# Evolution

## evolve()

Apply a sequence of admissible structural operators (Genesis/Decay) to a Knowledge Structure.

### Signature

```python
evolve(
    structure: KnowledgeStructure,
    operators: Iterable[StructuralOperator],
) -> KnowledgeStructure
```

### Operators

| Operator         | Description                                |
| ---------------- | ------------------------------------------ |
| `AddObject`      | Introduce a new KnowledgeObject            |
| `AddRelation`    | Introduce a new CanonicalRelation          |
| `RemoveObject`   | Remove a KnowledgeObject (and related relations) |
| `RemoveRelation` | Remove a CanonicalRelation                 |

### Example

```python
from cks.evolution import AddObject, AddRelation, compose

ops = [
    AddObject(new_object),
    AddRelation(new_relation),
]

evolved = evolve(structure, ops)
```

All operators are observationally pure — the original structure is never modified.

---

# Merging

## merge()

Three-way merge of independently evolved Knowledge Structures.

### Signature

```python
merge(
    base: KnowledgeStructure,
    branch_a: KnowledgeStructure,
    branch_b: KnowledgeStructure,
) -> KnowledgeStructure
```

### Example

```python
from cks import merge, MergeConflictError

base = KnowledgeStructure([obj1, obj2])
branch_a = KnowledgeStructure([obj1, obj3])   # evolved independently
branch_b = KnowledgeStructure([obj2, obj4])   # evolved independently

try:
    merged = merge(base, branch_a, branch_b)
except MergeConflictError as e:
    for conflict in e.conflicts:
        print(f"Conflict on {conflict.object_id}")
```

### MergeConflictError

Raised when `branch_a` and `branch_b` changed the same identity to different results. The `conflicts` attribute is a list of `MergeConflict` objects, each containing:

| Field      | Description                                      |
|------------|--------------------------------------------------|
| object_id  | The identity that both branches changed          |
| base       | The object in the common ancestor (or None)      |
| branch_a   | The object in branch A (or None if removed)      |
| branch_b   | The object in branch B (or None if removed)      |

---

# Reference Engine

The public interface internally delegates every operation to the Reference Engine.

Applications normally do not need to instantiate the engine directly.

However, it remains available:

```python
from cks import ReferenceEngine

engine = ReferenceEngine()
```

The engine provides the same canonical operations exposed by the module-level API.

---

# Exceptions

## SerializationError

Raised when canonical serialization cannot be parsed.

Example:

```python
from cks import SerializationError

try:
    structure = parse(text)
except SerializationError:
    ...
```

---

# ValidationResult

The validator returns an immutable `ValidationResult`.

Useful properties include:

| Property          | Description                         |
| ----------------- | ----------------------------------- |
| is_valid          | Overall validation status           |
| diagnostics       | Complete diagnostic collection      |
| error_count       | Number of errors                    |
| warning_count     | Number of warnings                  |
| information_count | Number of informational diagnostics |
| metadata          | Validation metadata                 |

Convenience methods include:

* `has_errors()`
* `has_warnings()`
* `has_information()`
* `summary()`

---

# Public Classes

The following classes are part of the supported public API.

| Class                | Purpose                         |
| -------------------- | ------------------------------- |
| ObjectIdentity       | Canonical identity              |
| KnowledgeObject      | Semantic object                 |
| CanonicalRelation    | Semantic relation               |
| KnowledgeStructure   | Immutable knowledge structure   |
| ValidationResult     | Validation outcome              |
| Diagnostic           | Validation diagnostic           |
| DiagnosticCollection | Immutable diagnostic collection |
| ReferenceEngine      | Reference implementation engine |
| SerializationError   | Serialization exception         |
| StructuralOperator   | Abstract base for evolution operators      |
| AddObject            | Genesis – add a KnowledgeObject            |
| AddRelation          | Genesis – add a CanonicalRelation          |
| RemoveObject         | Decay – remove a KnowledgeObject           |
| RemoveRelation       | Decay – remove a CanonicalRelation         |
| MergeConflict       | Describes a single merge conflict           |
| MergeConflictError  | Exception raised when merge conflicts occur |

---

### Copy and deepcopy behaviour

`KnowledgeObject`, `CanonicalRelation` and `KnowledgeStructure` are
deeply immutable by contract.  When used with `copy.copy` or
`copy.deepcopy` they return the same object (`self`) rather than
creating a new copy.  This is safe and intentional – no observable
state can be changed, so sharing the reference is indistinguishable
from cloning the object.

You can safely pass these objects to any library or store them in
containers that rely on `deepcopy` (for example `cks-runtime`'s
in‑memory storage).

---

# API Stability

The public API follows semantic versioning.

Within a major version:

* public function names remain stable;
* observable behaviour remains stable;
* canonical semantics remain stable.

Internal implementation details may evolve without affecting user code.

---

# Related Documentation

For additional information, see:

* **Getting Started** — installation and first steps.
* **Concepts** — semantic foundations.
* **Architecture** — implementation design.
* **Examples** — practical usage patterns.
* **Core Specifications** — formal normative definitions.
