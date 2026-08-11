# Contracts

This document describes the formal contract that connects every major
component of the Canonical Knowledge Structure (CKS) ecosystem.

## The Contract Chain

Every CKS implementation is governed by a single chain of
responsibilities:

1.  **Specification** (CKS‑001 – CKS‑009)
    Defines the canonical model: what a Knowledge Object is, how it is
    identified, what constitutes structural validity, and how knowledge
    evolves.

2.  **Validator** (CKS‑005, `cks.validator`)
    Realises the specification as a deterministic, observationally pure
    decision procedure.  The validator must accept every structure that
    satisfies the canonical constraints and reject every structure that
    violates one or more of them.

3.  **Test Suite** (`tests/`)
    Encodes the contract as executable assertions.  The suite contains
    both positive cases (valid structures that must be accepted) and
    negative cases (invalid structures that must be rejected).

4.  **Command‑Line Interface** (`cks.cli`)
    Exposes the validator to users and scripts.  The CLI does not
    introduce new semantics; it merely translates command‑line
    arguments into calls to the validator and formats the results.

5.  **Plugins** (`cks.plugin`, `cks.constraints`)
    Extend the validator with domain‑specific constraints.  Plugins
    are discovered at import time and must obey the same contract as
    built‑in constraints.

## Invariants

Every component in the chain must preserve the following invariants:

- **Determinism** – identical inputs always produce identical outputs.
- **Observational Purity** – validation never mutates the input.
- **Representation Independence** – behaviour depends only on
  canonical semantics, never on serialization format or programming
  language.
- **Traceability** – every diagnostic can be traced back to the
  specific constraint that produced it.

## Conformance

An implementation is conformant if and only if it passes the complete
test suite while using the canonical validator through the canonical
interface (CLI or Python API).  The test suite is the single source of
truth for conformance.

## Extending the Contract

New components (e.g., MCP servers, alternative language bindings) must
satisfy the same invariants and pass the same test suite to be
considered conformant.  The contract chain is designed to be extended
without modifying the existing links.