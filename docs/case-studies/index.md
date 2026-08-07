# Case Studies

Real-world scenarios that demonstrate how CKS prevents hallucinations,
tracks provenance, and gives LLMs a verifiable knowledge backbone.

| Case Study | What it shows |
|------------|---------------|
| [Catching Fake Citations](catching-fake-citations.md) | How CKS mechanically detects a fabricated source that an LLM would otherwise accept |
| [Semantic Search and Partial Merge](semantic-search-and-partial-merge.md) | How CKS resolves merge conflicts automatically using semantic embeddings, in-place updates, and partial three-way merges |
| [Ontology Validation and Graph Visualization](ontology-validation-and-visualization.md) | How CKS catches type errors with ontology constraints and debugs them with Mermaid visualization |
| [Contradiction Detection and Hypothesis Sandboxing](contradiction-detection-and-sandbox.md) | How CKS detects logical contradictions (mutual exclusion, functional relations) and safely tests fixes in isolated sandboxes |
| [Offline Semantic Search with Local Embeddings](local-embeddings.md) | How CKS switched to local, token-free embeddings and correctly ranked fruits above vehicles with cosine similarity 0.70 vs 0.21 |
| [Resolving a Reasoning Conflict with Inference Arbitration](inference-conflict-resolution.md) | How CKS detects, explains, and resolves competing `InferenceStep`s using the reasoning layer (ADR-001) |
| [Memory Agent: Saving and Reusing Knowledge Graphs Across Sessions](memory-agent-graph-reuse.md) | How CKS stores named graphs in a persistent registry, loads them in new conversations, and evolves them without rebuilding |
| [CRDT Fork Resolution with Fork Agent](crdt-fork-resolution.md) | How CKS detects and automatically resolves CRDT forks using MV‑Register, outbox tasks, and the autonomous ForkResolutionAgent |