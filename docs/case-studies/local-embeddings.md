# Case Study: Offline Semantic Search with Local Embeddings

**Problem:** Semantic search is a powerful tool for exploring a knowledge
graph, but until recently it required a Hugging Face API token. This
created a barrier for users who just wanted to try CKS, added a dependency
on an external service, and introduced a common failure mode — the token
was set in the user's shell but not inherited by the MCP server process
launched by Claude Desktop, leading to silent fallback to non-semantic
stub embeddings.

**CKS solution:** The new `FastEmbedEmbeddingClient` (backed by the
`fastembed` library and ONNX Runtime) runs a small, high-quality
sentence-transformers model **entirely locally** — no API token, no
network calls after the initial model download, and no external
dependency. It is now the **default** embedding provider in `cks-mcp`.
Combined with the existing background outbox worker and NumPy-vectorised
`search_embeddings`, semantic search works out of the box with zero
configuration.

---

## Scenario

We built a simple graph with three objects:

- **Apple** (Fruit)
- **Banana** (Fruit)
- **Car** (Vehicle)

We then ran a semantic search with the query `"fruit"` — without
providing any explicit seed IDs — to see whether the local embeddings
could correctly separate the fruits from the vehicle.

---

## Tools Used

- `validate_knowledge` — create the session and commit the initial version
- `search_semantic` — semantic search without `seed_ids`
- `get_metrics` — verify telemetry tracking

---

## What Happened

### 1. Graph created and validated

```
validate_knowledge(json_data)
→ valid: true, session_id: "5245c363…", version_id: "…"
```

Three objects were committed: `apple` (Fruit), `banana` (Fruit), `car`
(Vehicle).

### 2. Background embedding generation

The `OutboxEmbeddingWorker` detected the new version, extracted text
representations for each object, and generated embeddings using the
local `all-MiniLM-L6-v2` model. This took approximately 10–13 seconds
on first run (model warm-up).

### 3. Semantic search correctly separated fruits from vehicle

```
search_semantic(session_id, query="fruit")
→ matched_seeds: ["apple", "banana", "car"]
  scores: {apple: 0.705, banana: 0.671, car: 0.214}
```

The cosine similarity scores tell the story clearly:

- **Apple**: 0.705 — strongly matches "fruit"
- **Banana**: 0.671 — strongly matches "fruit"
- **Car**: 0.214 — correctly ranked lowest, semantically unrelated

All three objects were returned only because the graph contained
exactly 3 objects and the default `top_k=3` returned everything.
The scores themselves are what demonstrate correct semantic ranking.

### 4. Telemetry confirmed the tool calls

```
get_metrics() → tool_telemetry.tools.search_semantic
  calls: 2, success_rate: 0.5
```

Two calls were tracked: the first returned `not_found` (embeddings
hadn't been generated yet), the second succeeded. This is normal
behaviour immediately after session creation.

---

## Key Takeaways

- **Local embeddings work without any API keys.** The server downloaded
  a ~90 MB model on first use and ran fully offline from that point on.
- **Semantic quality is excellent.** A simple query like `"fruit"`
  clearly separated fruits (0.67–0.70) from a vehicle (0.21).
- **No configuration needed.** `fastembed` is the default provider — no
  environment variables, no API tokens, no setup.
- **The outbox worker needs a few seconds.** Embedding generation is
  asynchronous; a short wait after creating a session is normal.
- **Telemetry tracks everything.** `tool_telemetry` in `get_metrics`
  provides per-tool call counts, success rates, and latency percentiles
  for observability.

---

## Reproduce It Yourself

1. Install `cks-mcp` (v1.18.0+) and connect it to Claude Desktop.
2. The server will automatically use `fastembed` — no API keys required.
3. Start a chat and say:

   > Use cks‑mcp to create a small graph with a few objects of different
   > categories (e.g., fruits and vehicles). Then run `search_semantic`
   > with a query that clearly belongs to one category and show me the
   > similarity scores.

4. Observe the cosine similarity scores — objects matching the query
   category will have scores > 0.6, while unrelated objects will be
   near 0.2 or below.

No API tokens. No cloud services. Just a conversation.
