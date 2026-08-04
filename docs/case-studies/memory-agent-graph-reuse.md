# Case Study: Saving and Reusing Knowledge Graphs Across Sessions

**Problem:** Claude Desktop can build a project's knowledge graph (architecture,
modules, dependencies) using `cks-mcp` tools, but the graph's `session_id` is
lost when the chat ends. In a new conversation, the graph must be rebuilt from
scratch — wasting time and offering no guarantee the structure will be identical.
LLMs need "memory" of previously created graphs.

**CKS solution:** Memory Agent v1 — three new MCP tools (`register_graph`,
`get_graph`, `list_graphs`) and a `graph_registry` table in `cks-runtime`
(SQLite/Postgres). Now a graph can be given a meaningful name, saved, and
looked up in the next conversation — no rebuilding needed.

---

## Scenario

We have three CKS repositories (core, runtime, mcp) with hundreds of modules
and ADRs. We want to:

1. Build a single graph of the entire ecosystem.
2. Save it under the name `"cks-ecosystem"`.
3. In a new chat, load that graph and analyse it — find anomalies and propose
   next steps.
4. Fix the problems directly in the graph without rebuilding.

---

## Tools Used

- `construct_knowledge` / `validate_knowledge` — building and validating the graph.
- `register_graph` — saving the graph under a name.
- `get_graph` — loading the saved graph in a new conversation.
- `list_graphs` — listing all saved graphs.
- `evolve_knowledge` — fixing anomalies and extending the graph.
- `detect_contradictions` — checking for logical inconsistencies.
- `visualize_graph` — visualising the structure.

---

## What Happened

### 1. The ecosystem graph was built and saved

In the first conversation, Claude cloned the three repositories, analysed their
structure, and built a graph of 88 objects (nodes) and 96 relations (edges).
The graph included three components (core, runtime, mcp), their modules,
17 ADRs, and relations such as `depends_on`, `contains`, `implements`,
`publishes`, `resolves`.

The graph passed validation with no errors and was saved:

```
register_graph(name="cks-ecosystem", session_id="fc73af04...",
    description="Complete knowledge graph of the CKS ecosystem as of August 2026",
    tags="cks,ecosystem,architecture")
→ {"registered": true, "name": "cks-ecosystem"}
```

### 2. The graph was loaded in a new conversation

In a new chat, Claude called `get_graph("cks-ecosystem")` — and received the
same `session_id` as in the first conversation. The graph did not need to be
rebuilt. Memory Agent v1 worked.

### 3. Analysis revealed real problems

Using `visualize_graph` and `detect_contradictions`, Claude discovered:

- **Self-loop `publishes` relations**: `cks-core → cks-core` and
  `cks-mcp → cks-mcp` — instead of pointing to real target objects
  (SchemaModel, MCPServerEndpoint).
- **Asymmetric `resolves` relations**: `critic_agent` was linked only to
  `inference_staleness_sweeper`, although the codebase has handlers for all
  three staleness types (inference, provenance, temporal).
- **Missing `Outbox` object** as a distinct entity, despite
  `request_enrichment` referencing a "persistent outbox" in its description.
- **No `observability → runtime-metrics` connection** between the mcp and
  runtime layers.

### 4. The graph was fixed and extended

All issues were resolved through `evolve_knowledge` in the same session —
without rebuilding the graph, without losing existing data:

| Fix | Operations |
|---|---|
| Removed self-loop `publishes` | Deleted two relations, added `SchemaModel` and `MCPServerEndpoint` objects with correct `publishes` relations |
| Added `resolves` for all sweepers | 5 new relations from `critic_agent` and `enrichment_agent` to the three sweepers |
| Created explicit `Outbox` object | `Outbox` + `Task`, relations `contains`, `reads_from`, `writes_to` |
| Fixed misnamed relation | `rel-enrichment-resolves-outbox` → `rel-enrichment-uses-projection` |
| Added plugins | `FastEmbedPlugin`, `GossipPlugin`, interfaces `EmbeddingClient`, `GossipTransport` |
| Added observability relation | `observability --uses--> runtime-metrics` |

After all changes: **97 objects, 111 relations, 0 contradictions**.

---

## Key Takeaways

- **Memory Agent v1 works.** A graph built in one conversation was loaded
  in another without any loss. This solves the "rebuild from scratch" problem.
- **Graphs can be analysed and fixed without rebuilding.** All 24 evolution
  operations were applied to the existing session — versioning tracked every
  change.
- **The tools find real problems, not hypothetical ones.** Self-loop
  `publishes`, asymmetric `resolves`, missing `Outbox` object — these were not
  artificially created errors but real artefacts of the first graph-building
  pass, which automatic analysis identified and helped fix.
- **The graph is a living project artefact.** It can be updated as the
  codebase evolves, serve as architectural documentation, and act as a
  validator for future changes.

---

## Reproduce It Yourself

1. Install `cks-mcp` (v1.37.0+) and connect it to Claude Desktop.
2. In a first chat, build a graph of any project (or clone the CKS
   repositories) and save it via `register_graph`.
3. Open a new chat and load the graph via `get_graph`.
4. Analyse it with `visualize_graph` and `detect_contradictions`.
5. Fix any problems you find via `evolve_knowledge` and update the graph
   registration.

The whole process takes 10–15 minutes and requires zero lines of code —
just a conversation with Claude.
