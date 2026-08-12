# Contributing to Canonical Knowledge Structure (CKS)

Thank you for your interest in contributing to the Canonical Knowledge Structure (CKS) project.

CKS is an open specification and reference implementation whose primary goal is to establish a representation-independent semantic foundation for knowledge. Every contribution should therefore prioritize correctness, determinism, clarity, and long-term maintainability over implementation-specific optimizations.

---

# Guiding Principles

All contributions should follow the core principles of the CKS specifications:

* Representation Independence
* Structural Equivalence
* Observational Purity
* Deterministic Behaviour
* Canonical Semantics

Changes should preserve these principles whenever possible.

---

# Types of Contributions

Contributions are welcome in several areas, including:

* Specification improvements
* Documentation
* Reference implementation
* Validation rules
* Serialization
* Examples
* Tests
* Bug reports
* Design discussions

---

# Before Contributing

Before implementing a significant change, please:

1. Review the existing specifications.
2. Search existing Issues and Discussions.
3. Open a discussion when proposing substantial architectural changes.

Large semantic changes should preferably be discussed before implementation.

---

# Development Guidelines

The reference implementation emphasizes readability over cleverness.

Contributors are encouraged to:

* write clear, explicit code;
* keep modules focused;
* preserve deterministic behaviour;
* avoid unnecessary dependencies;
* maintain implementation independence.

Whenever practical, new functionality should include corresponding unit tests.

---

# Coding Style

The Python implementation follows modern Python practices:

* Python 3.12+
* type annotations
* immutable data structures where appropriate
* descriptive docstrings
* deterministic behaviour

Consistency is preferred over personal style.

---

# Commit Messages

Please use concise, descriptive commit messages.

Examples:

* Add canonical constraint registry
* Improve serialization validation
* Refactor ReferenceEngine inspection
* Update documentation for CKS-007

---

# Pull Requests

A good pull request should:

* address a single logical change;
* include relevant tests when applicable;
* update documentation if public behaviour changes;
* preserve backward compatibility unless an intentional specification revision requires otherwise.

---

# Reporting Issues

When reporting a bug, please include:

* Python version;
* operating system;
* steps to reproduce;
* expected behaviour;
* observed behaviour;
* complete traceback (if applicable).

---

# Specifications

The reference implementation follows the published CKS specifications.

If implementation behaviour and specification disagree, the specification takes precedence unless an official revision states otherwise.

---

# Community

CKS is intended to be an open, collaborative, and respectful project.

Constructive feedback, thoughtful discussion, and well-reasoned proposals are always appreciated.

Thank you for helping improve the Canonical Knowledge Structure project.
