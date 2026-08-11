# Canonical Knowledge Structure (CKS)

> **A universal, representation-independent semantic foundation for knowledge.**

The Canonical Knowledge Structure (CKS) project defines a formal semantic model for representing, validating, exchanging, and evolving knowledge independently of programming languages, document formats, databases, or artificial intelligence systems.

CKS separates **knowledge itself** from the representations used to store or communicate it.

---

# Why CKS?

The same knowledge is often duplicated across many incompatible representations.

* Documents
* Databases
* JSON
* XML
* Source code
* Knowledge graphs
* APIs
* AI prompts

Each representation describes the same concepts differently.

CKS introduces a canonical semantic layer shared by all representations.

```text
Knowledge
      │
      ▼
Canonical Knowledge Structure
      │
 ┌────┼───────────────┐
 ▼    ▼               ▼
JSON Python Database Natural Language
```

Representations may evolve over time.

The canonical knowledge remains unchanged.

---

# Design Principles

CKS is founded on four fundamental principles.

## Representation Independence

Knowledge exists independently of the syntax used to describe it.

JSON, Python objects, databases, and documents are merely different representations of the same underlying semantic structure.

---

## Canonical Semantics

Meaning is preserved through canonical structure rather than implementation-specific syntax.

---

## Deterministic Behaviour

Every canonical operation produces the same observable result for identical inputs.

---

## Observational Purity

Canonical operations never modify their inputs.

Construction, validation, serialization, comparison, and inspection are observationally pure.

---

# Project Architecture

The CKS ecosystem is organised as a family of independent specifications.

```text
CKS-000
    │
    ▼
CKS-001
    │
    ├─────────────┐
    ▼             ▼
CKS-002      CKS-003
    │             │
    └──────┬──────┘
           ▼
       CKS-004
           │
           ▼
       CKS-005
           │
           ▼
       CKS-006
           │
           ▼
       CKS-007
           │
           ▼
       CKS-008
           │
           ▼
       CKS-B001-PY
```

Each specification defines one canonical aspect of the ecosystem.

---

# Reference Implementation

This repository contains the official Python reference implementation.

Current components include:

* immutable semantic model;
* canonical serializer;
* validator with constraint registry;
* reference engine;
* structural evolution (Genesis/Decay operators);
* command-line interface (CLI);
* public interface;
* conformance tests (116 tests);
* reference corpus (valid and invalid examples);
* documentation.

---

# Documentation

The documentation is organised into several sections.

| Section         | Description                          |
| --------------- | ------------------------------------ |
| Getting Started | Installation and first steps         |
| Concepts        | Fundamental ideas and terminology    |
| Architecture    | Internal organisation of the project |
| API Reference   | Public Python interface              |
| Examples        | Practical usage examples             |
| Specifications  | Complete formal CKS specifications   |

---

# Learning Path

New users are encouraged to explore the project in the following order.

```text
Getting Started
       │
       ▼
Concepts
       │
       ▼
Architecture
       │
       ▼
API Reference
       │
       ▼
Examples (including CLI and Corpus)
       │
       ▼
Specifications
```

This progression introduces the conceptual foundations before the formal specification.

---

# Current Status

The CKS specifications are stable and continue to evolve through versioned releases.

The Python implementation serves as the first canonical implementation of the CKS ecosystem.

Completed milestones include:

* ✅ Core semantic model (CKS‑001)
* ✅ Canonical serialization (CKS‑003)
* ✅ Validation pipeline (CKS‑005)
* ✅ Reference Engine (CKS‑006)
* ✅ Canonical Knowledge Interface (CKS‑007)
* ✅ Structural Evolution (CKS‑004)
* ✅ Command-Line Interface
* ✅ Reference Corpus

Future work includes:

* additional reference implementations (Rust, TypeScript);
* extended constraint libraries;
* interoperability tooling;
* domain-specific knowledge models;
* SDK and plugin architecture.

---

# Open Source

CKS is developed as an open specification and open-source reference implementation.

Contributions are welcome.

See the following documents for additional information:

* CONTRIBUTING.md
* CODE_OF_CONDUCT.md
* SECURITY.md
* CHANGELOG.md
* ROADMAP.md

---

# License

The CKS reference implementation is released under the MIT License.