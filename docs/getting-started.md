# Getting Started

Welcome to the **Canonical Knowledge Structure (CKS)** project.

This guide introduces the core ideas behind CKS and walks through the first steps of using the Python reference implementation.

---

# What is CKS?

Canonical Knowledge Structure (CKS) is an implementation-independent framework for representing knowledge.

Unlike traditional data formats, CKS separates **knowledge** from its representation.

Instead of treating JSON, XML, databases, or programming languages as the primary representation, CKS defines a canonical semantic model that every representation can share.

```
Knowledge
      │
      ▼
Canonical Knowledge Structure
      │
 ┌────┼─────────────┐
 ▼    ▼             ▼
JSON Python      Database
```

The same knowledge can therefore be represented in multiple ways while preserving identical meaning.

---

# Installation

From PyPI (recommended):

```bash
pip install canonical-ks
```

Or from source:

```bash
git clone https://github.com/Deus-corp/CKS.git
cd CKS
pip install -e .
```

Verify the installation:

```python
import cks

print(cks.__version__)
```

---

# Your First Knowledge Object

A Knowledge Object consists of:

* a canonical identity;
* a semantic structure.

```python
from cks.core import ObjectIdentity
from cks.core import KnowledgeObject

identity = ObjectIdentity(
    id="definition-1",
    type="Definition",
    name="Knowledge"
)

obj = KnowledgeObject(
    identity=identity
)
```

---

# Building a Knowledge Structure

Knowledge Objects are collected into a Knowledge Structure.

```python
from cks.interface import construct

structure = construct([obj])
```

The resulting structure is immutable and can be safely inspected, validated, and serialized.

---

# Validation

Validate the structure using the canonical validator.

```python
from cks.interface import validate

result = validate(structure)

print(result.is_valid)
```

Diagnostics are available even for valid structures.

```python
for diagnostic in result.diagnostics:
    print(diagnostic)
```

Or use the command line:

```bash
cks validate examples/corpus/valid_theory_example.json
```

---

# Evolution

Knowledge Structures can be evolved through canonical structural operators.

```python
from cks.interface import evolve
from cks.evolution import AddObject

new_obj = KnowledgeObject(
    identity=ObjectIdentity(
        id="definition-2",
        type="Definition",
        name="New Knowledge"
    )
)

# Add a new object
evolved = evolve(structure, operators=[AddObject(new_obj)])
```

The original structure remains unchanged — evolution always returns a new structure.

---

# Serialization

Serialize the structure into canonical JSON.

```python
from cks.interface import serialize

json_text = serialize(structure)

print(json_text)
```

Deserialize it back.

```python
from cks.interface import parse

restored = parse(json_text)
```

The following property holds:

```
parse(serialize(S))
```

is structurally equivalent to

```
S
```

---

# Inspection

The reference engine provides several implementation-independent inspection operations.

```python
from cks.interface import inspect

summary = inspect(structure)

print(summary)
```

Additional operations include:

* `compare()`
* `extract()`
* `project()`
* `diagnose()`

---

# Running the Test Suite

Execute the complete reference test suite.

```bash
python -m pytest -v
```

Current status: 110 tests, all passing.

All tests should pass before contributing changes.

---

# Repository Structure

```
src/
    cks/
        core.py
        interface.py
        engine.py
        validator.py
        serialization.py
        diagnostics.py
        result.py
        evolution.py
        schema.py
        plugin.py
        cli/
            __init__.py
            formatters.py
        constraints/
            __init__.py
            base.py
            builtin.py
            registry.py
            structural.py
            semantic.py

docs/
examples/
    corpus/
        valid_theory_example.json
        invalid_duplicate_id.json
        invalid_dangling_reference.json
        invalid_derivation_cycle.json
    json/
        cks-schema.json
tests/
```

---

# Learn More

After completing this guide, the recommended reading order is:

1. Concepts
2. Architecture
3. API Reference
4. Examples
5. Core Specifications

These documents explain both the theory behind CKS and the design of the reference implementation.

---

# Design Principles

The Python reference implementation follows the principles defined by the CKS specifications.

Every public operation is designed to be:

* deterministic;
* observationally pure;
* implementation-independent;
* representation-independent.

These guarantees allow different implementations to produce identical observable behaviour while remaining free to choose their internal architecture.

---

# Next Steps

Continue with:

* **Concepts** — the semantic foundations of CKS.
* **Architecture** — the design of the reference implementation.
* **API Reference** — the complete public interface.
* **Examples** — practical usage patterns.
* **CLI Reference** — use `cks --help` for command-line usage.
