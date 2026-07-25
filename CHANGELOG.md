# Changelog

All notable changes to the Canonical Knowledge Structure (CKS) project are documented in this file.

The project follows a semantic versioning strategy where practical.

---

## [1.10.3] - 2026-07-25

### Fixed
- CI: added auto-fix step for ruff before lint check, resolving version mismatch between local and CI environments.

---

## [1.10.2] - 2026-07-25

### Fixed
- CI linting step (ruff) now passes cleanly after full auto-fix pass. No functional changes.

---

## [1.10.1] - 2026-07-25

### Fixed
- Applied `ruff` auto-fixes across the codebase (import sorting, deprecated type annotations, `__all__` ordering). No functional changes.

---

## [1.10.0] - 2026-07-25

### Added
- `UpdateObject` structural operator — modify an existing KnowledgeObject's structure in-place without cascading deletion of relations. Supports `merge` and `replace` modes.
- `resolutions` parameter for `KnowledgeStructure.merge()` — allows callers to specify per-object conflict resolutions, enabling partial merges.
- `MergeResolution` type alias for cleaner API.
- 18 new tests covering `UpdateObject`, `resolutions`, and merge edge cases.

### Fixed
- `RemoveRelation` now validates that the target ID belongs to a `CanonicalRelation`, preventing silent referential integrity violations when misused.

---

## [1.9.1] - 2026-07-22

### Fixed
- `query_subgraph` no longer produces dangling relations when a CanonicalRelation ID is passed as a seed – it now correctly returns an empty result.
- `query_subgraph` now preserves deterministic insertion order, eliminating PYTHONHASHSEED-dependent ordering.

---

## [1.9.0] - 2026-07-21

### Added
- `KnowledgeStructure.query_subgraph()` – extracts the local k-hop neighborhood around one or more seed ids as a self-contained subgraph (own `root_hash`, no dangling relations), with optional `include_relation_types`/`include_object_types` filters, and an optional `max_tokens`/`max_objects` budget with degree/type/distance-weighted candidate ranking when the neighborhood exceeds it.
- `SubgraphResult` – return type of `query_subgraph()`, pairing the extracted `structure` with `total_found_nodes`, `returned_nodes`, `is_truncated`, `truncation_reason`, and `suggested_next_seed`, so a caller can always tell a full neighborhood from a budget-truncated one and knows where to resume.
- `query_subgraph()` function in the public `cks.interface` module, delegating to `KnowledgeStructure.query_subgraph()`. `SubgraphResult` and `query_subgraph` now exported from the top-level `cks` package.
- 17 new tests covering traversal depth, multiple seeds, n-ary (hyperedge) relations, the two `include_*` filters, budget truncation under both `max_objects` and `max_tokens`, `type_weights` ranking, and the seeds-are-never-dropped guarantee.

---

## [1.8.2] - 2026-07-21

### Added
- `merge()` function in the public `cks.interface` module, delegating to `KnowledgeStructure.merge()`.
- `MergeConflict` and `MergeConflictError` now exported from the top-level `cks` package.

---

## [1.8.1] - 2026-07-21

### Added
- `KnowledgeStructure.merge()` – three-way merge of independently evolved structures with conflict detection via object hashes, referential integrity enforcement, and structured `MergeConflictError`.
- `MergeConflict` and `MergeConflictError` types, exported from the top-level `cks` package.
- `merge()` function in `cks.interface`, wired through `ReferenceEngine`.
- `KnowledgeObject._id_hash` – cached canonical hash of `identity.id`, making `KnowledgeStructure` construction ~10× faster.
- New tests for `identity_equivalent`, `_id_hash` caching, and merge (7 new tests, total 167 passed).

### Changed
- `KnowledgeStructure.__init__` now uses each object's cached `_id_hash` instead of recomputing `_canonical_hash(id)` for every object on every construction.
- `CanonicalRelation.__init__` sets `_id_hash` explicitly, matching the cache behaviour of `KnowledgeObject.__post_init__`.

---

## [1.8.0] - 2026-07-21

### Added
- `KnowledgeStructure.merge()` – three-way merge of independently evolved structures with conflict detection via object hashes, referential integrity enforcement, and structured `MergeConflictError`.
- `MergeConflict` and `MergeConflictError` types.
- `KnowledgeObject._id_hash` – cached canonical hash of `identity.id`, making `KnowledgeStructure` construction (and therefore every structural edit) ~10× faster.
- New tests for `identity_equivalent`, `_id_hash` caching, and merge (7 new tests, total 167 passed).

### Changed
- `KnowledgeStructure.__init__` now uses each object's cached `_id_hash` instead of recomputing `_canonical_hash(id)` for every object on every construction.
- `CanonicalRelation.__init__` sets `_id_hash` explicitly, matching the cache behaviour of `KnowledgeObject.__post_init__`.

---

## [1.7.0] - 2026-07-20

### Added
- Merkle‑tree based canonical hashing for `KnowledgeObject` and `KnowledgeStructure`, enabling O(1) structural equivalence comparison.
- `KnowledgeStructure.diff(target)` method that computes a correct, ordered list of structural operators to evolve the structure into `target`, handling cascading relation deletions.
- `KnowledgeStructure.__hash__` is now implemented, allowing structures to be used as dictionary keys or set members.
- `KnowledgeStructure.root_hash` property for external comparison and logging.

---

## [1.6.0] - 2026-07-19

### Added
- `VerificationRecordIntegrityConstraint` (OPTIONAL) – validates the shape of `VerificationRecord` objects, ensuring exactly one `verified_by` relation, a well-formed `checked_at` timestamp, a valid `checked_via` method, a correct `http_status` when present, and no qualitative judgment fields.
- `OPTIONAL_CONSTRAINTS_BY_NAME` dictionary for stable name-based lookup of optional constraints (e.g., `"embedding_projection"`, `"verification_record"`).
- 12 new tests for the verification constraint (total 150 tests).

---

## [1.5.0] - 2026-07-18

### Added
- `extra_constraints` parameter to `validate()`, `validate_all()`, `structural_validate()`, `semantic_validate()`, `evaluate_constraints()`, `ReferenceEngine.validate()`, and `ReferenceValidator.validate()`. Allows opting in additional constraints for a single call without mutating the global registry.
- `ReferenceValidator._STAGE_ORDER` and `_scoped_registry()` to support scoped constraint execution.
- Five new tests validating scoped constraint behaviour and non-interference with the global registry (total 138 tests).

---

## [1.4.0] - 2026-07-18

### Added
- `EmbeddingProjectionIntegrityConstraint` — optional constraint for validating vector-space projections of Knowledge Objects (requires exactly one `represents` relation to an existing source and an external `store_ref`).
- `OPTIONAL_CONSTRAINTS` set in `builtin.py` – not auto‑registered, opt‑in per validator.
- Comprehensive tests for the new constraint (11 new tests).

### Changed
- Bumped test suite to 134 tests.

---

## [1.3.1] - 2026-07-18

### Fixed
- Removed dead code in `DerivationCycleConstraint.dfs()` – an unused loop left over from the previous fix.

---

## [1.3.0] - 2026-07-18

### Fixed
- **Severity comparison** now uses numeric priority instead of lexicographic string comparison, so warnings no longer incorrectly invalidate structures (bug #4).
- **DerivationCycleConstraint** no longer crashes with `KeyError` when a `derives` relation references a non-existent participant — dangling references are now safely ignored by the cycle detector (bug #3).
- **Schema CLI** (`cks schema validate`) now works after `pip install cks-core` — the canonical JSON schema is bundled as package data and loaded via `importlib.resources` (bug #5).

### Changed
- Schema file moved from `examples/json/` to `src/cks/schemas/` and declared as package data in `pyproject.toml`.

---

## [1.2.2] - 2026-07-18

### Added
- Public function `parse_operations` in `cks.evolution` for deserializing JSON operation descriptors into `StructuralOperator` objects. Used by CLI, `cks-mcp`, and any other adapter that receives evolution requests over the wire.

---

## [1.2.1] - 2026-07-18

### Fixed
- Validation pipeline no longer double‑counts diagnostics. The `CONSTRAINTS` stage now evaluates only constraints tagged with that stage, instead of re‑evaluating all registered constraints.

---

## [1.2.0] - 2026-07-18

### Fixed
- `copy.deepcopy` no longer raises `TypeError` for `KnowledgeObject` and `KnowledgeStructure` (resolved `cannot pickle 'mappingproxy' object`). These immutable types now return `self` on copy, which is safe and fixes integration with `cks-runtime`'s `InMemoryStorage`.
- Added 4 regression tests for copy/deepcopy behaviour.

---

## [1.1.2] - 2026-07-17

### Changed
- Repository renamed from `CKS` to `cks-core`.
- Updated all internal and ecosystem links to new repository URL.
- Added "Ecosystem" table to README.

---

## [1.1.1] - 2026-07-14

### Changed

- Renamed PyPI distribution package from `canonical-ks` to `cks-core`
  to align with the `cks-*` ecosystem naming convention.
  Python import remains `import cks`.

---

## [1.1.0] - 2026-07-14

### Added

- `--strict` flag for CLI to fail on plugin loading errors.
- `mypy` static type checking in CI/CD (strict for core modules).
- `docs/contracts.md` — formal contract chain documentation.
- `_normalize_structure()` in `core.py` for explicit structural comparison.
- Contract tests for plugin system (`tests/test_plugin.py`).
- Type annotations for core modules.

### Changed

- `CanonicalRelation` now validates `participants` and `relation_type` explicitly.
- CLI refactored into modular commands (`cli/commands/`).
- Plugin system replaced `stderr print` with structured `logging`.
- Removed Python <3.9 fallback from `plugin.py`.
- `mypy` configuration: strict only for core modules.
- Development status updated to `Production/Stable` in `pyproject.toml`.

### Fixed

- CanonicalRelation no longer silently ignores conflicting structure keys.
- CLI error handling improved for missing files and invalid operations.
- mypy type errors resolved across core modules.

### Testing

- All 119 tests passing.

---

## [1.0.1] - 2026-07-14

### Added

#### Import/Export Adapters

- JSON‑LD → CKS converter (`cks convert`).
- CKS → JSON‑LD converter (`cks export`).
- Turtle → CKS converter (`cks convert`).
- CKS → Turtle converter (`cks export`).
- RDF/XML → CKS converter (`cks convert`).
- CKS → RDF/XML converter (`cks export`).

#### CI/CD and Developer Tooling

- Pre-commit hooks for automatic CKS validation.
- CI pipeline with test matrix (Python 3.12, 3.13, 3.14).
- Linting with ruff.
- Pre-commit checks in CI.

### Changed

- Public API stabilised for 1.0.0 release.
- Package renamed to `canonical-ks` on PyPI (import remains `cks`).

### Testing

- All 114 tests passing.

---

## [0.9.0] - 2026-07-14

### Added

#### Advanced Validation

- `validate_all()` — batch validation of multiple Knowledge Structures.
- `--min-severity` option (error/warning/information) for configurable severity thresholds.
- HTML output formatter (`--format html`).
- Markdown output formatter (`--format markdown`).

#### CLI Improvements

- `validate` command now accepts multiple input files (`nargs="+"`).
- Severity map and formatter map integrated into CLI pipeline.
- Batch mode aggregates results across all input files.

### Changed

- `validate()` signature extended with optional `min_severity` parameter.
- `validate_all()` accepts `min_severity` parameter.
- `interface.py` exposes new `validate_all` function.

### Fixed

- Various import and name resolution issues in `interface.py`.

### Testing

- All 110 tests passing.

---

## [0.8.6] - 2026-07-14

### Changed

- Renamed PyPI distribution package to `canonical-ks` (Python import remains `import cks`).
- Updated `pyproject.toml` with correct package name and dependencies.

### Fixed

- Resolved PyPI publication name conflict by renaming distribution to `canonical-ks`.

---

## [0.8.0] - 2026-07-14

### Added

#### Plugin Architecture

- External constraint discovery via `importlib.metadata` entry points.
- `cks.plugin` module for loading plugins at import time.
- `cks plugin list` CLI command to inspect registered constraints.
- `docs/plugins.md` — guide for creating and distributing constraint plugins.

#### API Stabilization

- Evolution operators (`AddObject`, `AddRelation`, `RemoveObject`, `RemoveRelation`, `compose`) promoted to public API.
- Full `__all__` declarations across all public modules.
- `cks.interface.evolve` now accepts `operators` instead of `add`/`remove` keyword arguments.

#### Documentation

- Added `docs/plugins.md` (Plugin Development Guide).
- Updated `docs/api.md` with evolution operators and plugin references.

#### Testing

- All 110 tests passing.

---

## [0.7.0] - 2026-07-14

### Added

#### CLI (Command-Line Interface)

- `cks validate` command with `--format` (text/json) and `--output` options.
- `cks parse` command for quick structural inspection.
- `cks inspect` command with text and JSON output modes.
- `cks evolve` command applying structural evolution from JSON operation files.
- Structured `cks.cli` package with extensible formatters (`formatters.py`).

#### Structural Evolution (CKS-004)

- `StructuralOperator` abstract base class with `OperatorContract`.
- `AddObject` and `AddRelation` (Genesis operators).
- `RemoveObject` and `RemoveRelation` (Decay operators).
- `compose()` for chaining multiple operators.
- Integration into `ReferenceEngine.evolve()`.

#### Constraints Refactoring

- Moved constraint implementations to domain-specific modules (`structural.py`, `semantic.py`) matching Validation Domains (CKS‑005).
- Converted `builtin.py` into a manifest that imports and instantiates canonical constraints.
- Removed duplicate registration logic; constraints are now registered exclusively through `builtin.py`.

#### Reference Corpus

- Initial canonical examples under `examples/corpus/`:
  - `valid_theory_example.json`
  - `invalid_duplicate_id.json`
  - `invalid_dangling_reference.json`
  - `invalid_derivation_cycle.json`

#### Documentation

- Updated `README`, `ROADMAP`, `CHANGELOG`, `CONTRIBUTING`.
- Updated `docs/`: Getting Started, API Reference, Architecture, Concepts, Examples, Index.
- Added CLI usage and evolution to all documentation.

#### Testing

- 11 unit tests for `evolution.py`.
- 13 CLI integration tests (`tests/test_cli.py`) covering all commands and formats.
- Total test suite: 116 tests passing.

---

## [0.1.0] - 2026-07-13

### Added

#### Core Implementation

* Initial immutable implementation of `ObjectIdentity`
* Initial immutable implementation of `KnowledgeObject`
* Initial implementation of `CanonicalRelation`
* Initial implementation of `KnowledgeStructure`
* Structural equivalence support

#### Serialization

* Canonical JSON serializer
* Canonical JSON deserializer
* Round-trip serialization support
* Canonical serialization validation
* `SerializationError`

#### Validation

* Reference validation pipeline
* Structural validation
* Semantic validation
* Referential integrity validation
* Derivation cycle detection
* Constraint registry
* Immutable `ValidationResult`
* Canonical diagnostics

#### Reference Engine

* Initial `ReferenceEngine`
* Knowledge construction
* Inspection
* Comparison
* Projection
* Extraction
* Evolution interface
* Validation integration

#### Public API

* Canonical public interface (`cks.interface`)
* Stable package exports
* Public construction API
* Public serialization API
* Public validation API
* Public inspection API

#### Testing

* Comprehensive unit test suite
* Core tests
* Serialization tests
* Validator tests
* Engine tests
* Public interface tests

#### Documentation

* Complete README
* CONTRIBUTING guide
* Repository metadata
* Public API documentation
* Project overview

---

### Notes

This is the first public release of the Canonical Knowledge Structure (CKS) reference implementation.

The implementation provides the initial executable realization of the CKS Core Specifications and establishes the foundation for future development of canonical constraints, reference corpora, documentation, and additional language implementations.