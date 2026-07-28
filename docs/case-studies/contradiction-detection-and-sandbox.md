# Case Study: Contradiction Detection and Hypothesis Sandboxing

**Problem:** A knowledge graph can accumulate logically inconsistent statements — for example, the same source–target pair might be linked by both `confirms` and `refutes` relations, or a planet might be asserted to orbit two different stars. Standard structural and even type‑level validation passes such graphs without complaint, because every individual edge looks well‑formed. The contradiction only becomes visible when multiple relations are read *together*.

**CKS solution:** The new `mutual_exclusion` and `functional_relation` extension constraints (introduced in `cks-core` 1.13.0) let a graph *declare* what counts as a contradiction, and the `detect_contradictions` tool surfaces those violations in a compact, machine‑readable form. The `fork_sandbox` tool provides an isolated “what‑if” branch — apply a hypothesis, see the diff, and keep or discard the result — without ever touching the parent session. Together with the existing `suggest_evolution` preview mode, these tools give LLMs a full **explore–detect–fix–validate** loop inside a single conversation.

---

## Scenario

We built a small scientific graph about the exoplanet candidate **Kepler‑22b**:

- **Kepler‑22b** (Planet) orbits **Kepler‑22** (Star).
- Two **ConfirmationReport** objects represent independent analyses of the planet.
- A `MutualExclusionRule` declares that `confirms` and `refutes` are mutually exclusive — a planet cannot be both confirmed and refuted by the *same* report.
- Deliberately, we added **both** a `confirms` and a `refutes` relation from Kepler‑22b to each report, creating exactly the kind of joint nonsense the rule exists to catch.

We then used the new tools to detect the contradictions, fix one in a sandbox, preview an unrelated evolution, and verify that the parent session remained untouched.

---

## Tools Used

- `validate_knowledge` — initial session creation
- `evolve_knowledge` — graph construction
- `detect_contradictions` — surface mutual‑exclusion and functional‑relation violations
- `fork_sandbox` — isolated branch with hypothesis + diff from fork point
- `suggest_evolution` (preview mode) — dry‑run candidate operations
- `close_session` — discard the sandbox

---

## What Happened

### 1. Contradiction detection — mutual exclusion

With the `MutualExclusionRule` in place, calling `detect_contradictions` on the session returned:

```json
{
  "contradiction_count": 2,
  "contradictions": [
    {
      "code": "CKS-EXT-MUTUAL-EXCLUSION",
      "severity": "error",
      "message": "Relation '…' (type 'confirms') and relation '…' (type 'refutes') both connect 'kepler-22b' to 'report-A', but a MutualExclusionRule declares these relation_types mutually exclusive."
    },
    {
      "code": "CKS-EXT-MUTUAL-EXCLUSION",
      "severity": "error",
      "message": "… same for report-B …"
    }
  ]
}
```

Two contradictions — one per report — exactly as expected.

### 2. Contradiction detection — functional relation

A separate test with a `FunctionalRelationRule` for `orbits` and two `orbits` edges from Earth to different stars also returned:

```json
{
  "contradiction_count": 1,
  "contradictions": [
    {
      "code": "CKS-EXT-FUNCTIONAL-RELATION",
      "severity": "error",
      "message": "Source 'earth' has 2 distinct targets via functional relation_type 'orbits' …"
    }
  ]
}
```

### 3. Sandbox fix with `fork_sandbox`

We asked `fork_sandbox` to create a branch and remove the `refutes` relation to report‑A:

```json
{
  "sandbox_session_id": "d42dcc57-…",
  "operations_applied": 1,
  "diff_from_fork_point": {
    "summary": {"added_objects": 0, "removed_objects": 0, "added_relations": 0, "removed_relations": 1},
    "operations": [{"type": "remove_relation", "relation_id": "rel-refutes-1"}]
  },
  "message": "Sandbox session '…' is an isolated fork … nothing here affects the parent."
}
```

Re‑running `detect_contradictions` inside the sandbox showed **1** contradiction (report‑B still conflicted), while the parent session still reported **2** — proving full isolation.

### 4. Preview mode with `suggest_evolution`

Passing a candidate operation list (add a moon “Kepler‑22b‑I” + an `orbits` relation) to `suggest_evolution` in preview mode returned:

```json
{
  "would_apply": true,
  "operations_previewed": 2
}
```

No version was created — the preview mode validated the structure without committing anything.

### 5. Error handling in the sandbox

When we attempted to add a duplicate object ID inside a sandbox, the tool immediately returned:

```json
{
  "error": "evolution_failed",
  "message": "Hypothesis could not be applied: Object 'obj-1' already exists."
}
```

The sandbox was automatically discarded, leaving the parent session untouched.

### 6. Ontology validation still works alongside contradictions

As a regression check, we validated a graph where Earth orbits Pasta (type Food) with `type_hierarchy` and `relation_type` extensions enabled. The system correctly returned `valid: false` with diagnostic code `CKS-EXT-RELATION-TYPE`, confirming that the new contradiction layer composes cleanly with the existing ontology layer.

---

## Key Takeaways

- **Contradictions are explicit, not guessed.** `MutualExclusionRule` and `FunctionalRelationRule` objects define what counts as a contradiction, so the system never flags something the domain expert didn't declare.
- **Sandboxes are safe by construction.** `fork_sandbox` never mutates the parent; a failed hypothesis automatically discards the branch.
- **Preview saves versions.** `suggest_evolution` in preview mode validates candidate operations without committing — no wasted versions or sessions.
- **Isolation is guaranteed.** The parent session's contradiction count did not change while the sandbox fixed its copy.
- **Composability.** Contradiction detection works alongside the existing ontology, provenance, and structural validators — all opt‑in, all additive.

---

## Reproduce It Yourself

1. Install `cks‑mcp` (v1.12.1+) and connect it to Claude Desktop.
2. Start a chat and say:

   > Use cks‑mcp to build a small graph about an exoplanet candidate.  
   > Include a MutualExclusionRule that declares “confirms” and “refutes” as mutually exclusive.  
   > Link the planet to two ConfirmationReport objects using both relation types, then call `detect_contradictions` and show me the result.  
   > Next, `fork_sandbox` to remove one conflicting relation and prove the parent session is untouched.  
   > Finally, preview adding a new moon with `suggest_evolution`.

3. Observe the contradiction count drop in the sandbox, the isolation from the parent, and the preview response — all without writing a single line of code.
