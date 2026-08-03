# Case Study: Resolving a Reasoning Conflict with Inference Arbitration

**Problem:** Documentation and roadmaps drift over time. A project's
`ROADMAP.md` claims one status, its `CHANGELOG.md` shows another, and a
human reader is left to guess which source to trust. CKS's reasoning
layer (ADR-001) is designed to model exactly this: competing
`InferenceStep`s that conclude the same fact but disagree, with a
structured process to detect, rank, and resolve the conflict.

**CKS solution:** `InferenceConfidenceConflictConstraint` detects the
disagreement, `explain_knowledge` shows the competing chains,
`arbitrate_inference_conflict` resolves it with an explicit winner, and
`visualize_graph` renders the final belief state — all without a single
LLM call from the server (the client is the LLM).

---

## Scenario

A developer reads `cks-core/ROADMAP.md` and finds two contradictory
statements about version 1.4: the "Current Status" section claims it is
complete, while the "Version 1.4" checklist still marks it as planned.
Checking `CHANGELOG.md` reveals the actual releases have long surpassed
1.4. We model this as three competing `InferenceStep`s and resolve them
using only the MCP tools.

---

## Tools Used

- `validate_knowledge` — create the session and base concepts
- `evolve_knowledge` — add three competing InferenceSteps + enable
  `inference_confidence_conflict` extension
- `explain_knowledge` — inspect the active steps for a disputed concept
- `arbitrate_inference_conflict` — resolve the conflict by picking a winner
- `visualize_graph` — render the final reasoning graph

---

## What Happened

### 1. Base facts recorded

Three concepts were created: `cks-core`, `cks-runtime`, `cks-mcp` (as
`Component` objects), with `depends_on` relations between them.

### 2. Three competing InferenceSteps added

Each step concluded `"Is cks-core v1.4 complete?"` but with different
`operator`, `confidence`, and `justification`:

| Step ID | Source | Operator | Confidence | Claim |
|---------|--------|----------|------------|-------|
| step-roadmap-planned | ROADMAP checklist | deductive | 0.3 | NOT complete |
| step-roadmap-status | ROADMAP status paragraph | heuristic | 0.6 | complete |
| step-changelog | CHANGELOG.md dated entries | inductive | 0.95 | complete and far surpassed |

`evolve_knowledge` was called with `extensions: ["inference_confidence_conflict"]`.
The response included `diagnostics` containing `CKS-EXT-INFERENCE-CONFIDENCE-CONFLICT`
(severity: warning), confirming the three-way disagreement was detected.

### 3. Conflict explained

`explain_knowledge` with `object_id` set to the conclusion showed all three
`active_steps`, ranked by entrenchment (confidence descending). The ROADMAP
checklist claim (0.3) was ranked last, the CHANGELOG claim (0.95) first.

### 4. Conflict resolved by arbitration

`arbitrate_inference_conflict` was called with `winner_id: "step-changelog"`
and `commit: true`. The other two steps received `superseded_by:
"step-changelog"`. No LLM call was made — the client itself supplied the
winner based on the policy criteria (source specificity, datedness,
independence).

### 5. Final graph rendered

`visualize_graph` confirmed the new belief state: one active inference
(step-changelog), two superseded steps, and the three `next_milestone`
relations pointing to the real remaining work identified by comparing
ROADMAP against CHANGELOG.

---

## Key Takeaways

- **`InferenceConfidenceConflict` works on real-world documentation drift.**
  The same mechanism designed for scientific/legal reasoning caught a
  genuine inconsistency in the project's own status tracking.
- **No LLM call needed for arbitration.** The `arbitrate_inference_conflict`
  tool's `winner_id` parameter lets the calling client (already an LLM)
  supply its own decision, avoiding an extra API round-trip.
- **The reasoning layer is readably auditable.** `explain_knowledge` with
  `object_id` returns the full chain of evidence (premises, justification,
  confidence) for every competing step, so a human reviewer can
  independently verify the decision.
- **Extend the pattern to any multi-source disagreement.** The same flow
  applies to conflicting sensor readings, contradictory witness statements,
  or disagreeing expert opinions — wherever multiple sources conclude the
  same fact with different confidence.

---

## Reproduce It Yourself

1. Install `cks-mcp` (v1.28.0+) and connect it to Claude Desktop.
2. Start a chat and say:

   > Use cks‑mcp to create a session with two simple concepts. Then use
   > `evolve_knowledge` to add two `InferenceStep`s that conclude the same
   > object but disagree on confidence. Include
   > `extensions: ["inference_confidence_conflict"]`. Then use
   > `explain_knowledge` with the conclusion's `object_id` to see the
   > active steps. Pick a winner and call `arbitrate_inference_conflict`
   > with `winner_id` and `commit: true`. Finally, use `explain_knowledge`
   > again to confirm only the winner remains active.

3. Observe the `diagnostics` warning after step 2, and the `superseded_steps`
   in the final explanation.