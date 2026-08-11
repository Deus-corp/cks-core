# Changelog

All notable changes to the Canonical Knowledge Structure (CKS) project are documented in this file.

The project follows a semantic versioning strategy where practical.

---

## [1.21.1] - 2026-08-11

### Added
- **Documentation CI/CD** – automated GitHub Actions workflow that builds cks-studio's static demo and publishes it alongside the mkdocs site on GitHub Pages.
- **Demo page** (`docs/demo.md`) – link to the interactive ecosystem graph demo in the documentation navigation.

---

## [1.21.0] - 2026-08-04

### Added
- **`LayeringRuleConstraint`** – new opt-in extension constraint in `cks.constraints.layering` (`cks.constraints.builtin.OPTIONAL_CONSTRAINTS_BY_NAME["layering_rule"]`, identity `CKS-EXT-LAYERING-RULE`). Checks every `depends_on` relation between recognized CKS ecosystem components against a hardcoded layering order (`cks-core < cks-runtime < cks-mcp`) and raises an `ERROR` when a dependency points upstream (e.g. `cks-core → depends_on → cks-runtime`), mechanically catching what was previously enforced only by `pyproject.toml` and developer discipline. Relations naming components outside the recognized set, or with a relation type other than `depends_on`, are left untouched. See ADR-004 ("Layering Rule Constraint") for the design rationale.

### Fixed
- The `LayeringRuleConstraint` draft compared layer indices with the wrong operator (`source_layer >= target_layer`), which inverted the check: it flagged every *correct* dependency (e.g. `cks-runtime → cks-core`) and silently passed every *reverse* one (e.g. `cks-core → cks-runtime`). Corrected to `source_layer <= target_layer` before registering the constraint.

---

## [1.20.0] - 2026-08-04

### Added
- **`TemporalValidityConstraint`** – new opt-in extension constraint in `cks.constraints.temporal` (`cks.constraints.builtin.OPTIONAL_CONSTRAINTS_BY_NAME["temporal_validity"]`, identity `CKS-EXT-TEMPORAL-VALIDITY`). Checks every object's `structure` for an optional `valid_until` field (ISO-8601 datetime string, UTC-normalized); a `valid_until` in the past raises a `WARNING` (the fact is still structurally valid, just temporally expired), a malformed value raises an `ERROR`. Deliberately minimal — no interval reasoning or temporal logic — and answers exactly one question: "has this fact expired?" See ADR-003 ("Temporal Validity Constraint") for the design rationale, including how this lays the groundwork for a future `temporal_staleness_sweeper` in `cks-runtime`, mirroring `InferenceStalenessSweeper` (ADR-009).

---

## [1.19.0] - 2026-08-02

### Added
- **`ResolveInferenceConflict`** – new `StructuralOperator` in `cks.evolution` (wire format: `{"type": "resolve_inference_conflict", "conclusion_id": ..., "winner_id": ...}`). The write-side counterpart to `InferenceConfidenceConflictConstraint`/`rank_by_entrenchment`/`explain_inference`, which only detect and rank a confidence conflict but never write `superseded_by`. Given a `conclusion_id` and the `winner_id` an arbiter (human or agent) has chosen, supersedes every *other* active `InferenceStep` concluding `conclusion_id` in favor of the winner as a single atomic evolution — instead of the caller hand-rolling one `UpdateObject` per losing step and risking missing one, mis-targeting the wrong conclusion, or superseding an already-retired step into a cycle. `winner_id` is checked eagerly (apply-time) to be an existing, active `InferenceStep` that actually concludes `conclusion_id`; an already-superseded step found concluding `conclusion_id` is left untouched, matching `InferenceConfidenceConflictConstraint`'s own exclusion of non-active steps from the conflict. A no-op if `winner_id` is already the only active step (the conflict was already resolved). Cannot itself introduce a `superseded_by` cycle, by construction.

---

## [1.18.0] - 2026-08-02

### Added
- **`explain_inference(structure, object_id, *, max_depth=25)`** – new pure query function in `cks.constraints.reasoning`. Answers ADR-001's Problem #3 ("`explain_diff`/`explain_knowledge` have no native 'why'"): walks every active `InferenceStep` chain concluding `object_id` back through each step's `premises`, recursively, down to base facts. Reports `operator`/`confidence`/`justification`/`alternatives_considered` per step, distinguishes a meta-reasoning citation of another `InferenceStep` id from an ordinary premise, and separately reports `superseded_steps` (the belief's revision history). Guards against `premises`/`conclusion` cycles (which `SupersessionChainConstraint` cannot see, since it only tracks `superseded_by` chains) and unbounded depth via `max_depth`, marking incomplete branches `truncated: "cycle" | "max_depth"`. Produces no `Diagnostic` and never mutates the structure, matching `rank_by_entrenchment`'s convention (which it reuses for ordering active steps by entrenchment).

---

## [1.17.0] - 2026-08-01

### Added
- **`StalePremiseConstraint`** – new opt-in extension constraint in `cks.constraints.reasoning` (`cks.constraints.builtin.OPTIONAL_CONSTRAINTS_BY_NAME["stale_premise"]`, identity `CKS-EXT-STALE-PREMISE`). Flags an *active* `InferenceStep` whose `premises` directly cite another `InferenceStep` id that has itself already been `superseded_by` a successor. Reported at WARNING severity: the cited step still exists and is still well-formed, so this is a meta-reasoning citation worth a second look, not a structural invalidity.
- **`SupersessionChainConstraint` cycle detection** – the existing constraint now also rejects a `superseded_by` cycle (e.g. `A.superseded_by == B`, `B.superseded_by == A`), reported once per distinct cycle at the constraint's existing ERROR severity, regardless of which member is reached first.
- **`rank_by_entrenchment(structure, conclusion_id)`** – new pure query function in `cks.constraints.reasoning`, not a `Constraint`. Ranks the active `InferenceStep`s sharing a conclusion by `confidence` (descending, structure order as tiebreak) for a caller resolving an `InferenceConfidenceConflictConstraint` WARNING. Produces no `Diagnostic` and never writes `superseded_by` — ranking, not automatic resolution.

See ADR-002 ("Belief Revision Support") for the design rationale, including why a premise sharing a *conclusion* (rather than an id) with a fully-superseded step turns out to be unreachable on valid data and isn't what `StalePremiseConstraint` checks.

---

## [1.16.0] - 2026-07-31

### Added
- **`InferenceConfidenceConflictConstraint`** – new opt-in extension constraint in `cks.constraints.reasoning` (`cks.constraints.builtin.OPTIONAL_CONSTRAINTS_BY_NAME["inference_confidence_conflict"]`, identity `CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT`). Flags two or more *active* (non-`superseded_by`) `InferenceStep` objects that share a `conclusion` but disagree on `confidence`. Reported at WARNING severity, not ERROR: this is a resolvable belief conflict between agreeing inference paths, distinct from the hard, ERROR-severity contradictions in `contradiction.py`. This is the `detect_contradictions` extension point ADR-001 named as its natural next step.

---

## [1.15.2] - 2026-07-31

### Added
- **Inference reasoning constraints** – new opt-in extension module `cks.constraints.reasoning` with `InferenceReferentialIntegrityConstraint`, `ConfidenceBoundsConstraint`, and `SupersessionChainConstraint`. Validates that `InferenceStep` objects reference existing premises/conclusions, carry numeric confidence scores in [0,1], and maintain valid supersession chains.
- **`RecordInference` operator** – records a new `InferenceStep` object with explicit premise and conclusion references. Integrated into `parse_operations`, `compose`, and the CLI.

---

## [1.15.1] - 2026-07-31

### Security
- **RDF/XML "billion laughs" hardening** – `RdfToCksConverter` now rejects any input containing a DOCTYPE declaration when parsing XML-based RDF formats, preventing exponential entity-expansion DoS attacks.

### Fixed
- **CLI `convert` and `evolve`** no longer crash with raw tracebacks on malformed input; they report clean error messages.
- **`ValidationResult.summary()`** no longer appends "0 informational messages" for results that have no informational diagnostics.
- **`query_subgraph()` determinism** – candidate ranking tie-breaker now uses object id instead of hash-dependent set ordering, eliminating cross-process variations.
- **n-ary relation export** – `CksToJsonLdConverter` and `CksToRdfConverter` now raise a clear error for relations with 3+ participants instead of silently dropping data.
- **Plugin constraint registration** – `load_external_constraints()` now handles duplicate identity collisions gracefully under `strict=False` (logs a warning instead of crashing `import cks`).
- **`validate_all`** is now accessible as `cks.validate_all()` and is covered by tests.

### Changed
- **Single version source** – `pyproject.toml`, `cks.__version__`, and `ReferenceEngine.VERSION` all read from `src/cks/_version.py`.

---

## [1.15.0] - 2026-07-30

### Added
- **Constraint entry points** – `[project.entry-points."cks.constraints"]` declared in `pyproject.toml`, completing the plugin contract so third-party packages can register custom constraints without manual registry calls.
- **Format versioning (CKS-003 §7)** – `serialize` now writes `_cks_format_version`, `_cks_min_reader_version`, and `_cks_metadata` into every JSON output. `parse` validates that the installed `cks-core` meets the file's minimum version requirement and raises a clear `FormatVersionError` when it doesn't.
- **`cks migrate` CLI command** – re-serializes legacy (pre‑v1.15.0) CKS JSON files into the current versioned format. Supports `--in-place` and `--check` flags.
- **`is_legacy_format()`** on `CanonicalDeserializer` – lets callers detect files produced by older serializers.
- **`FormatVersionError`** exported from `cks.serialization` and top‑level `cks`.

---

## [1.14.0] - 2026-07-30

### Added
- **`RenameObject` operator** – changes an object's `identity.name` without affecting its `id`, `type`, or any relations. Fully supported in `parse_operations`, `compose`, and the CLI.
- Public properties for all structural operators (`AddObject.obj`, `RemoveObject.object_id`, `UpdateObject.object_id`, etc.) – allows safe, documented introspection of operators by external consumers (cks-runtime, cks-mcp).

---

## [1.13.1] - 2026-07-29

### Fixed
- `ReferenceEngine.project()` (and the public `cks.project()`) now guarantees referential integrity: relations are included in the projection only if all their participants are present in the selected set, matching the behaviour of `query_subgraph`. Previously, a projection could contain dangling references.

---

## [1.13.0] - 2026-07-28

### Added
- **Contradiction-detection layer:** two new optional constraints, `mutual_exclusion` and `functional_relation`, that validate a graph against declared contradiction rules the same way `type_hierarchy`/`relation_type` validate against a declared type ontology.
  - `MutualExclusionRule` objects declare two relation_types that must never both connect the same ordered (source, target) pair (e.g. `supports` and `contradicts`).
  - `FunctionalRelationRule` objects declare a relation_type as single-valued per source (e.g. a planet may only `orbit` one star).
- New `MutualExclusionConstraint` and `FunctionalRelationConstraint` in `cks.constraints.contradiction`.
- 17 new tests for the contradiction constraint suite.

---

## [1.12.1] - 2026-07-28

### Fixed
- `schema.py` restored after accidental truncation; the module was missing the tail of `validate_json()`, causing import failures. Re-added the missing lines and verified correctness.
- Added `tests/test_schema.py` with 4 basic tests to prevent future regressions.

---

## [1.12.0] - 2026-07-27

### Added
- **Ontology/type-hierarchy layer:** new optional constraints `type_hierarchy` and `relation_type` that validate objects against a declared `TypeDefinition` hierarchy (`is_a`) and restrict relations to allowed domain/range types.
- New `TypeHierarchy`, `TypeHierarchyCycleConstraint`, and `RelationTypeConstraint` in `cks.constraints.ontology`.
- **CKS-009 specification:** formal document describing the Reference Knowledge Corpus (`examples/corpus/`).
- 20 new tests for the ontology constraint suite.

---

## [1.11.4] - 2026-07-27

### Added
- `UpdateObject` now exported from the top-level `cks` package (`from cks import UpdateObject` works).

### Fixed
- CLI `evolve` command now supports `update_object` operations via the canonical `parse_operations`, fixing a regression where the CLI's duplicated parser silently ignored `update_object`.
- `DerivationCycleConstraint` rewritten iteratively to avoid `RecursionError` on long derivation chains (>1000 edges).
- CLI `validate` with multiple files now respects `--format` and `--output` instead of always printing a plain-text summary.
- `format_markdown` formatter now correctly interpolates the valid/invalid status (missing f‑string prefix).
- `Diagnostic.metadata` now fully recursive‑frozen (via `core._freeze_mapping`), closing a gap where nested dicts remained mutable.
- `compose()` now applies a list of operators in a single pass over a shared object dict, avoiding O(n·N) rebuilds of `KnowledgeStructure` — typical batch evolves are ~320× faster.

---

## [1.11.3] - 2026-07-27

### Fixed
- `mypy.ini`'s `exclude` pattern had an indentation error that broke config parsing entirely — mypy silently fell back to scanning all 36 source files (including `cli/`, `adapters/`, and other modules meant to be excluded from strict checking) instead of the intended 16, and `ignore_missing_imports` wasn't being honored either, surfacing a spurious "stubs not installed" warning for `jsonschema`. Fixed the indentation so the config parses and applies as intended.
- `KnowledgeStructure.diff()` constructed `AddRelation` from a statically-typed `KnowledgeObject` where a `CanonicalRelation` was required; the invariant held at runtime (ids are pre-filtered to relations), but wasn't visible to the type checker. Added an explicit `isinstance` assertion so a future refactor of that filtering can't silently break the invariant, and so it type-checks under strict mode.
- Added missing generic type arguments (`tuple[...]`, `set[str]`, `dict[str, Any]`) in `core.py` and `evolution.py`, needed for `mypy --strict` to pass on the `cks.core`/`cks.constraints` modules per `mypy.ini`.

### Added
- `mypy` now runs in CI (`typecheck` job), per the ROADMAP item for this version line. `types-jsonschema` added to the `dev` extra so local runs get real stubs instead of relying solely on `ignore_missing_imports`.

---

### Fixed
- `KnowledgeStructure.merge()` now correctly rejects `resolutions` for identities that both branches touched but converged to the same value, matching the documented contract.

---

## [1.11.1] - 2026-07-26

### Fixed
- `CanonicalRelation.__init__` now rejects bare strings/bytes as `participants`, preventing silent corruption when a caller forgets to wrap a single ID in a list.
- `min_severity=INFORMATION` now correctly invalidates structures with INFORMATION-severity diagnostics, matching the CLI's documented behavior.
- Added 6 regression tests: 4 for relation participant validation, 2 for `min_severity`.

---

## [1.11.0] - 2026-07-25

### Added
- `KnowledgeStructure.merge()` now accepts an optional `dropped_relations` output parameter, recording IDs of relations silently excluded due to referential integrity.
- Dedicated unit tests for `merge()` in `tests/test_merge.py`.

### Fixed
- Documented that relations with vanished participants are dropped during merge, and made this visible to callers.

---

## [1.10.6] - 2026-07-25

### Fixed
- `cks.merge()` wrapper now passes the `resolutions` keyword argument through to `KnowledgeStructure.merge()`, enabling partial merge support from the public API.

---

## [1.10.5] - 2026-07-25

### Added
- README updated to reflect new features: `query_subgraph`, `UpdateObject`, and partial merge with `resolutions`.

---

## [1.10.4] - 2026-07-25

### Fixed
- Final ruff lint compliance: replaced `ValueError`/`RuntimeError` with `TypeError` for type-checking operators, removed unused import, and optimized list operation.

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