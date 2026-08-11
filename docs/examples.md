# Examples

The CKS reference implementation includes a **Reference Corpus** of
canonical examples demonstrating valid and invalid Knowledge Structures.

These examples are used for testing, learning, and as a baseline for
conformance verification.

All corpus examples can be found under `examples/corpus/`.

---

# Reference Corpus

The corpus provides a growing set of canonical structures:

| File | Description | Valid? |
|------|-------------|--------|
| `valid_theory_example.json` | A small theory with definitions, axioms, theorems, and proofs. | ✅ |
| `invalid_duplicate_id.json` | Two objects with the same canonical identity. | ❌ |
| `invalid_dangling_reference.json` | A relation referencing a non-existent object. | ❌ |
| `invalid_derivation_cycle.json` | Derivation relations forming a cycle (A → B → C → A). | ❌ |

# Using the CLI

The command-line interface provides quick access to validation and
inspection.

**Validate a structure:**

```bash
cks validate examples/corpus/valid_theory_example.json
```

Expected output:

```
✅ Valid
Errors: 0  Warnings: 0  Info: 0
```

**Validate with JSON output:**

```bash
cks validate examples/corpus/valid_theory_example.json --format json
```

**Inspect a structure:**

```bash
cks inspect examples/corpus/valid_theory_example.json
```

**Parse a structure:**

```bash
cks parse examples/corpus/valid_theory_example.json
```

---

# Evolution Examples

Knowledge Structures can be evolved using structural operators.

**Create an operations file** (`add_lemma.json`):

```json
[
  {
    "type": "add_object",
    "identity": { "id": "lemma-1", "type": "Lemma", "name": "New Lemma" },
    "structure": {}
  }
]
```

**Apply the evolution:**

```bash
cks evolve examples/corpus/valid_theory_example.json add_lemma.json
```

The command outputs the evolved structure as canonical JSON.

Multiple operators can be chained in a single operations file:

```json
[
  { "type": "add_object", "identity": { "id": "obj-1", "type": "Definition", "name": "X" }, "structure": {} },
  { "type": "add_object", "identity": { "id": "obj-2", "type": "Definition", "name": "Y" }, "structure": {} },
  {
    "type": "add_relation",
    "identity": { "id": "rel-1", "type": "Relation", "name": "depends" },
    "participants": ["obj-1", "obj-2"],
    "relation_type": "depends_on"
  }
]
```

---

### Extension Constraints

CKS ships with optional constraints that are not active by default.
For example, the `EmbeddingProjectionIntegrityConstraint` validates
vector‑space projections of Knowledge Objects.

To enable it in your code:

```python
from cks.constraints.builtin import OPTIONAL_CONSTRAINTS
from cks.constraints.registry import registry

for constraint in OPTIONAL_CONSTRAINTS:
    registry.register(constraint)
```

See the Plugin Development Guide for more details.

---

# Canonical Workflow

Most applications follow the same sequence of operations.

```text
Construct / Parse
      │
      ▼
Validate
      │
      ▼
Inspect / Diagnose
      │
      ▼
Evolve (optional)
      │
      ▼
Serialize
      │
      ▼
Exchange
```

Each operation is deterministic and observationally pure.

---

# Running the Test Suite

All corpus examples are verified by the automated test suite:

```bash
python3 -m pytest -v
```

Current status: 134+ tests passing.

---

# Related Documentation

- **Getting Started** — installation and first steps.
- **API Reference** — complete public interface.
- **Architecture** — implementation design.
- **Concepts** — semantic foundations.
