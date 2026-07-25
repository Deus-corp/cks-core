# Case Study: Semantic Search and Partial Merge

**Problem:** Managing a knowledge graph with multiple contributors leads to
conflicts — two people (or two LLM agents) editing the same concept
simultaneously. Traditional tools force a manual resolution of every
conflict, blocking the entire merge until all are resolved.

**CKS solution:** `merge_branch` now accepts a `resolutions` parameter,
enabling partial three-way merges. The caller specifies per-object
strategies (`"branch_a"`, `"branch_b"`, `None`, or a custom object),
and the merge commits immediately, without manual intervention for the
resolved identities. Combined with semantic search and in-place
`update_object`, this enables a fully automated knowledge workflow.

---

## Scenario

We built a knowledge graph about machine learning with five concepts
(Neural Networks, Backpropagation, Support Vector Machines, Training Data,
GPU) and four relations (`trained_by`, `uses`, `accelerated_by`).
We then:

1. Used `search_semantic` to find "how to optimize neural network training"
   without specifying any object IDs — the system returned relevant concepts
   like Backpropagation and GPU.
2. Updated GPU's description in place via `update_object` — no cascade
   deletion of relations.
3. Created a branch and made divergent edits to Neural Networks' description.
4. Merged the branch back with `resolutions={"neural-networks": "branch_b"}` —
   the merge succeeded in one call, no manual conflict resolution required.
5. Extracted the final graph with `query_subgraph` in compact mode.
6. Audited the runtime with `get_metrics`.

---

## Tools Used

- `validate_knowledge` and `evolve_knowledge` (with `update_object`)
- `search_semantic` (no seed IDs)
- `create_branch`, `merge_branch` (with `resolutions`)
- `query_subgraph` (compact mode)
- `get_metrics`

---

## What Happened

### 1. Semantic search without seed IDs

```
search_semantic(query="how to optimize neural network training")
```

Returned `neural-networks`, `backpropagation`, and `svm` as the top semantic
matches. GPU appeared in the expanded subgraph via its `accelerated_by`
relation, confirming the embedding model correctly associates GPU with
neural network optimization even though it wasn't a top-3 seed.

### 2. In-place object update

```
evolve_knowledge(operations=[{"type": "update_object", "object_id": "gpu",
  "structure_patch": {"description": "specialized hardware for parallel matrix
  operations, essential for accelerating neural network training and optimization"}}])
```

GPU's description changed without cascading to its relations —
`accelerated_by` remained intact, no manual relation reconstruction needed.

### 3. Branching and divergent edits

Branch A set Neural Networks to *"deep learning models with many hidden layers"*.
The original session set it to *"computational graphs inspired by biological
neurons, including both shallow and deep architectures"*. This is a genuine
conflict: same object, same field, diverged from the same base version.

### 4. Partial merge with resolutions

```
merge_branch(target_session_id=..., source_session_id=...,
  resolutions={"neural-networks": "branch_b"})
```

The merge succeeded immediately with `"merged": true`. No `conflicts` array,
no second call needed. The resolved object carried the branch's description,
confirming `"branch_b"` was honored correctly.

### 5. Compact subgraph extraction

```
query_subgraph(seed_ids=["neural-networks"], depth=2, compact_mode=true)
```

Returned all 5 nodes and 4 edges in a flat `nodes`/`edges` format — ideal
for LLM consumption, with no redundant canonical wrappers.

### 6. Runtime metrics

```
get_metrics()
```

Reported 6 `evolve` calls, 2 `query_subgraph` calls, and 2 `merge` calls,
with average execution times of 0.13 ms, 0.15 ms, and 0.09 ms respectively.

---

## Key Takeaways

- **Semantic search works without explicit IDs.** The embedding model correctly
  associates concepts by meaning, not just keywords.
- **`update_object` enables surgical edits.** No need to remove and re-add
  objects with cascading relation deletions.
- **Partial merge eliminates manual conflict resolution.** With `resolutions`,
  the merge commits in one call for all specified identities.
- **Compact mode reduces token usage.** Flat `nodes`/`edges` arrays are
  smaller and faster for LLMs to process than full canonical JSON.
- **Metrics provide observability.** Invocation counts and execution times
  are available for every operation type.

---

## Reproduce It Yourself

1. Install `cks-mcp` and connect it to Claude Desktop.
2. Start a chat and say:  
   `Use cks-mcp to create a knowledge graph about machine learning with 5 concepts and 4 relations. Then branch, make divergent edits, and merge with resolutions.`
3. Observe the conflict being resolved automatically.

No coding required.
