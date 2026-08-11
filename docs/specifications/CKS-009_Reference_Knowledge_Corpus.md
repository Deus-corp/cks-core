# Introduction

## Purpose

The purpose of this specification is to describe the Reference
Knowledge Corpus: the fixed set of example Knowledge Structures
shipped with the Python Reference Implementation under
`examples/corpus/`.

Previous Core Specifications define the semantic model (CKS‑001),
construction (CKS‑002), serialization (CKS‑003), evolution (CKS‑004),
validation (CKS‑005), the Reference Engine (CKS‑006), the Canonical
Knowledge Interface (CKS‑007), and conformance (CKS‑008).

This document does not define new canonical behaviour. It describes
the worked examples used to demonstrate, exercise, and regression-test
that behaviour.

## Scope

This specification defines:

- the purpose of the Reference Knowledge Corpus;
- the categories of example it contains;
- the naming convention that determines which category a given file
  belongs to;
- the minimum categories a conformant corpus shall provide.

Individual example files are illustrative content, not normative
text; adding, removing, or editing an example does not change any
canonical semantics defined by CKS‑001..CKS‑008.

## Position within CKS

| Document | Title | Role |
|----------|-------|------|
| CKS-000 | Canonical Foundations and Terminology | Philosophical principles and unified terminology |
| CKS-001 | Core Specification | Formal semantic model |
| CKS-002 | Canonical Construction Specification | Construction methodology |
| CKS-003 | Canonical Serialization | Machine‑processable representation |
| CKS-004 | Canonical Structure Evolution | Admissible structural evolution |
| CKS-005 | Validator Specification | Formal model of canonical validation |
| CKS-006 | Reference Engine Specification | Computational engine architecture |
| CKS-007 | Canonical Knowledge Interface (CKI) | Canonical operations and interaction |
| CKS-008 | Reference Conformance Specification | Unified conformance criteria |
| **CKS-009** | **Reference Knowledge Corpus** | **Worked examples used to demonstrate and test conformance** |

CKS‑008 is the final *normative* specification in the Core CKS
series. CKS‑009 is deliberately informative: it documents fixtures,
not rules.

## Normative Status

This specification is **informative**. It describes what the
Reference Knowledge Corpus is and how its examples are organised. It
imposes no obligation on any implementation beyond what CKS‑001..
CKS‑008 already require. A conformant implementation is never
required to reuse these exact files; it is only expected that, were
it to validate them, the outcome (valid/invalid, and which
constraint fired) would match what each file's category promises.

---

# The Reference Knowledge Corpus

## Purpose

Canonical behaviour is easiest to demonstrate, and easiest to break by
accident, in the presence of concrete worked examples. The Reference
Knowledge Corpus exists so that:

- every constraint defined by CKS‑001/CKS‑005 has at least one example
  that exercises it;
- the conformance test suite (CKS‑008) has fixed, version-controlled
  input rather than ad-hoc inline literals scattered across test
  files;
- documentation (`docs/cks-core/examples.md`, the project README) can
  point at a real file instead of a fabricated snippet that may drift
  from what the implementation actually accepts.

## Location

The corpus lives under `examples/corpus/` in the Python Reference
Implementation repository. Two related, but distinct, directories
exist alongside it and are out of scope for this specification:

- `examples/json/` — a minimal JSON Schema example and the smallest
  possible valid document, used for schema validation demonstrations
  rather than constraint coverage.
- `scripts/validate_cks.py` — a standalone script that consumes
  corpus files; it is tooling, not corpus content.

## Categories

Every file in the corpus belongs to exactly one of the following
categories, identified by its filename.

### `valid_*`

A Knowledge Structure that satisfies every constraint in
`BUILTIN_CONSTRAINTS`. `valid_theory_example.json` is the canonical
worked example: a small theory graph (`Definition`, `Axiom`,
`Theorem`, `Proof` objects connected by `depends_on` and `derives`
relations) chosen to be readable by a human reviewer while still
exercising both structural and semantic validation stages.
`valid_theory_export.ttl` is the Turtle projection of the same
structure, demonstrating that export preserves canonical semantics
across representations (CKS‑001, "Representation preserves
structure").

### `invalid_*`

A Knowledge Structure that is expected to fail validation for exactly
one, named reason. The filename identifies the constraint the example
exists to exercise:

| File | Constraint exercised |
|------|----------------------|
| `invalid_duplicate_id.json` | `CKS-STRUCT-UNIQUE-IDENTITY` |
| `invalid_dangling_reference.json` | `CKS-STRUCT-DANGLING-REF` |
| `invalid_derivation_cycle.json` | `CKS-SEM-CYCLE` |

An `invalid_*` file shall fail for its named reason and shall not
incidentally fail for an unrelated one; conformance tests built on top
of these files are expected to assert on the specific diagnostic
identity, not merely on `is_valid is False`.

### `evolve_*`

A structural evolution operation list, in the format accepted by
`cks evolve` / `cks.evolution.parse_operations`, meant to be applied
to a `valid_*` file. `evolve_add.json` demonstrates a Genesis
operation (`add_object`) applied on top of
`valid_theory_example.json`.

### Format/adapter examples (`person.*`)

`person.cks.json`, `person.jsonld`, `person.rdf`, `person.ttl`, and
`person_from_rdfxml.cks.json` are the same minimal Knowledge Structure
expressed in, or round-tripped through, every format the adapters in
`cks.adapters` support (JSON‑LD, Turtle, RDF/XML). These exist to
demonstrate CKS‑001's representation-independence claim concretely:
the same canonical structure survives conversion in either direction.

## Minimum Corpus Requirement

A conformant Reference Implementation's corpus shall provide, at
minimum:

1. one `valid_*` example exercising both the STRUCTURAL and SEMANTIC
   validation stages;
2. one `invalid_*` example per constraint registered in
   `BUILTIN_CONSTRAINTS`;
3. one `evolve_*` example per structural operator category (Genesis,
   Decay) defined by CKS‑004.

Optional constraints (`OPTIONAL_CONSTRAINTS`, e.g. the
`embedding_projection` and `verification_record` extensions) are not
covered by this minimum; their own test suites (see
`tests/test_constraints_projection.py`,
`tests/test_constraints_verification.py`) carry inline fixtures
instead of corpus files, since those examples are extension-specific
rather than part of the shared reference corpus.

## Relationship to the Conformance Test Suite

CKS‑008 defines *that* an implementation must be tested for
conformance; this specification defines *what the shared fixtures
for that testing look like*. `tests/` may still construct
`KnowledgeObject`/`KnowledgeStructure` instances inline where a corpus
file would be a heavier dependency for a narrow unit test — the
corpus is the shared, documented set of examples, not the exclusive
source of test input.

---

# Informative References

[CKS-000] Canonical Knowledge Structure — Canonical Foundations and Terminology.

[CKS-001] Canonical Knowledge Structure — Core Specification.

[CKS-004] Canonical Knowledge Structure — Canonical Structure Evolution.

[CKS-005] Canonical Knowledge Structure — Validator Specification.

[CKS-008] Canonical Knowledge Structure — Reference Conformance Specification.