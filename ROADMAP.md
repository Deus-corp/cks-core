# CKS Roadmap

This roadmap outlines the planned evolution of the Canonical Knowledge Structure (CKS) ecosystem.

The roadmap is intentionally incremental. Each release aims to preserve backward compatibility whenever possible while extending the canonical specifications and the reference implementation.

---

# Guiding Direction

The long-term objective of CKS is to provide a universal, representation-independent semantic foundation for knowledge that can be shared across:

* humans
* software systems
* databases
* programming languages
* knowledge graphs
* artificial intelligence

The reference implementation evolves together with the formal CKS specifications.

---

# Current Status (August 2026 — v1.21.1)

The project has progressed well beyond the original version-by-version roadmap below. Verified against `CHANGELOG.md`:

- **MCP Server (`cks-mcp`):** implemented, shipped as an independent, actively maintained repository (currently v1.28.0) with 27 tools — **done**.
- **Merge engine:** three-way merge with conflict detection (`KnowledgeStructure.merge()`) — **done** (v1.8.0).
- **Belief revision / reasoning engine (ADR-001, ADR-002):** `InferenceStep` objects, the `inference_confidence_conflict` and `stale_premise` extension constraints, `rank_by_entrenchment`, `explain_inference`, and the `resolve_inference_conflict` evolution operator — **done** (v1.16.0–v1.19.0). This is the mechanism `cks-mcp` uses for its conflict-resolution tools.
- **Event system, time-travel operations, delta version storage, Merkle-tree hashing/structural diff** — **done**.
- **Temporal validity checking (ADR-003):** opt-in `temporal_validity` extension constraint flagging objects with an expired `valid_until` — **done** (v1.20.0). Groundwork for a future `temporal_staleness_sweeper` in `cks-runtime`.
- **Ecosystem layering rule (ADR-004):** opt-in `layering_rule` extension constraint mechanically enforcing the `cks-core < cks-runtime < cks-mcp` dependency direction on `depends_on` relations, previously only enforced by convention — **done** (v1.21.0).
- **Documentation publishing pipeline:** CI workflow builds `cks-studio`'s static demo and publishes it alongside the mkdocs site on GitHub Pages — **done** (v1.21.1).

**Note on version numbering:** actual shipped releases (currently 1.19.0) no longer track the thematic `0.x`/`1.x` plan below 1:1 — work has shipped faster and in a different order than originally sequenced, and the section headers below (Version 1.4, 1.5, ...) should be read as *thematic milestones*, not as promises about which release number they'll land in. This document previously said Version 1.3 was current and described AI/LLM Integration (originally planned as "Version 1.4") as unstarted future work, while a separate summary paragraph in the same file claimed it was already done — an internal contradiction caused by this document not being updated as fast as the code. Both are corrected below.

---

# Version 0.2 — Constraints ✅ (completed)

* Canonical constraint framework
* Built-in constraint library (structural and semantic)
* Constraint registration API
* Canonical constraints: unique identity, dangling reference, derivation arity, derivation cycle

---

# Version 0.3 — Documentation ✅ (completed)

* Complete user documentation (README, CONTRIBUTING, CHANGELOG, ROADMAP)
* Architecture guide
* API reference (public modules)
* Concepts guide
* Examples directory with reference corpus

---

# Version 0.4 — Knowledge Evolution ✅ (completed)

* CKS-004 reference implementation (`evolution.py`)
* Structural evolution engine (`StructuralOperator`, `OperatorContract`)
* Genesis operators: `AddObject`, `AddRelation`
* Decay operators: `RemoveObject`, `RemoveRelation`
* Operator composition (`compose`)
* CLI integration (`cks evolve`)
* Evolution tests (11 unit tests)

---

# Version 0.5 — Reference Corpus ✅ (completed)

* Initial reference knowledge corpus (`examples/corpus/`)
* Valid examples (`valid_theory_example.json`)
* Invalid examples: duplicate identity, dangling reference, derivation cycle
* Evolution operation examples

---

# Version 0.6 — CLI and Developer Tooling ✅ (completed)

* Command-line interface (`cks` command)
* Commands: `validate`, `parse`, `inspect`, `evolve`
* Output formatters: JSON, Plain Text
* `--output` option for file export
* CLI integration tests (13 tests)
* Total test suite: 116 tests passing

---

# Version 0.7 — SDK and Public API ✅ (completed)

* Stabilized public API (`cks.interface`)
* Complete Python SDK documentation
* Evolution operators promoted to public API
* Plugin architecture for custom constraints
* JSON Schema validation (`cks schema validate`)
* Full `__all__` declarations across public modules

---

# Version 0.8 — Advanced Validation ✅ (completed)

* Configurable severity thresholds (`--min-severity`)
* HTML and Markdown report formatters
* Batch validation of multiple structures (`validate_all`)
* Automated CI/CD pipeline (GitHub Actions)
* PyPI publication (`canonical-ks`)

---

# Version 0.9 — Ecosystem and Integrations ✅ (completed)

* Pre-commit hooks for CKS validation
* JSON‑LD, Turtle, RDF/XML import (`cks convert`)
* JSON‑LD, Turtle, RDF/XML export (`cks export`)
* CI/CD pipeline (GitHub Actions)
* Linting (ruff) and pre-commit checks in CI

---

# Version 1.0 — First Stable Release ✅ (completed)

* Stable public API
* Complete reference implementation
* Complete documentation
* Canonical constraint library
* Mature validation engine
* Reference corpus
* Conformance suite (114 tests)
* Long-term API stability guarantees
* PyPI publication (`canonical-ks`)

---

# Version 1.1 — Production Readiness ✅ (completed)

* Fix `CanonicalRelation` to explicitly validate `participants` and `relation_type`.
* Change development status to `Production/Stable` in `pyproject.toml`.
* Formalize that canonical identity is determined by `id` only.
* Remove Python <3.9 fallback from `plugin.py`.
* Replace stderr print with structured logging in `plugin.py`.

---

# Version 1.2 — CLI Modularization ✅ (completed)

* Split `cli/__init__.py` into separate handlers (`cli/commands/`).
* Add schema validation layer for operation files.
* Improve user-facing error messages in CLI.
* Add `--strict` flag for plugin failures.

---

# Version 1.3 — Contract Strengthening ✅ (completed)

* Extract `_normalize_structure()` for explicit structural comparison.
* Document the contract "specification → validator → tests → CLI → plugins".
* Add `mypy` type-checking to CI.
* Write contract tests for the plugin system.
* Create reference plugin examples.

---

# Version 1.4 — AI/LLM Integration (MCP Server) ✅ (completed)

* Implement CKS MCP Server. *(shipped as the separate `cks-mcp` repository, now at v1.28.0)*
* Provide standard MCP tools: `construct_knowledge`, `validate_knowledge`, `query_relations`/`query_subgraph`, `compare_structures`/`compare_versions`, `evolve_knowledge`, and 20+ more.
* Publish the server as a separate package (`cks-mcp`).

Also delivered as part of this phase, beyond the original scope: the belief-revision/reasoning engine (`InferenceStep`, `inference_confidence_conflict`, `resolve_inference_conflict`, `explain_inference`) that underpins `cks-mcp`'s conflict-resolution tools.

---

# Version 1.5 — Semantic Tools (next up)

Planned work — verified **not yet started** (no matching implementation in `CHANGELOG.md` as of v1.21.1):

* Build reasoning tools on top of CKS (pathfinding across relations, concept similarity).
* Expose semantic tools via MCP and CLI.

---

# Version 1.6 — Advanced SDK & Developer Experience

Planned work:

* Develop CKS Studio (lightweight web UI for constructing and validating Knowledge Structures).
* Add more adapters (OWL, CSV, Markdown tables).
* Begin client libraries for TypeScript and Rust.

---

# Version 1.7 — IDE Integration

Planned work:

* VS Code extension with syntax highlighting, autocompletion, and inline validation.

---

# Version 1.8 — Distributed Knowledge Spaces

Planned work:

* Enable linking and synchronizing multiple Knowledge Structures across different sources.

> Note: `cks-runtime`/`cks-mcp` have already shipped gossip-based replication between runtime nodes (ADR-008) — this item is about extending that to `cks-core`-level Knowledge Structure linking/synchronization specifically, which is distinct and still open.

---

# Version 1.9 — Versioning and Merging

Planned work:

* Implement Git-like versioning, branching, and merging for Knowledge Structures.

> Note: three-way merge (`KnowledgeStructure.merge()`) and branch/merge orchestration (`create_branch`/`merge_branch` in `cks-mcp`) already shipped. Remaining scope here, if any, should be re-scoped against what's already delivered before further planning.

---

# Version 2.0 — The Semantic Foundation

Planned goals:

* Fully distributed CKS ecosystem.
* Stable MCP and semantic tools.
* Multi-language SDKs.
* IDE support.
* Large-scale knowledge repositories.
* Integration with major AI platforms.

---

# Project Philosophy

CKS favors long-term stability over rapid feature growth.

New functionality is added only when it preserves the core principles of:

* Representation Independence
* Structural Equivalence
* Observational Purity
* Deterministic Behaviour
* Canonical Semantics

The roadmap may evolve as the specifications mature and the community grows.
