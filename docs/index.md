# Canonical Knowledge Structure

> A universal, representation-independent foundation for verifiable AI knowledge.

CKS is an open ecosystem that gives LLMs a **canonical knowledge backbone**. Every piece of information must be explicitly structured, validated against formal constraints, and traceable to its origin. This eliminates hallucinations and makes AI-generated knowledge auditable.

---

## How It Works

```
Your LLM (Claude Desktop, etc.)
        │
        ▼
    cks-mcp ─── Model Context Protocol server
        │
        ▼
 cks-runtime ─── Sessions, transactions, version history
        │
        ▼
   cks-core ─── Immutable semantic engine
```

## Key Capabilities

- **Eliminate citation hallucinations** – mechanically detect references to non-existent sources.
- **Ensure verification integrity** – cryptographic signing guarantees that source checks actually happened.
- **Full audit trail** – every operation is captured in an immutable version history.
- **Time-travel debugging** – list versions, compare them, and safely roll back to any previous state.
- **Branch, merge, and sandbox** – isolate an experiment from the main line, reconcile it with a three-way merge, or throw it away.
- **Real semantic search** – find knowledge by meaning, not keywords, via HuggingFace embeddings.
- **LLM-friendly API** – native MCP server with 24 tools, plus MCP Resources and Prompts, fully compatible with Claude Desktop and other MCP clients.

## Projects

| Project | Description | Status |
|---------|-------------|--------|
| [cks-core](cks-core/index.md) | Semantic engine – immutable knowledge objects, validation, evolution | v1.15.0 |
| [cks-runtime](cks-runtime/index.md) | Operational environment – sessions, transactions, versioning, events | v1.24.0 |
| [cks-mcp](cks-mcp/index.md) | MCP server – exposes CKS to LLMs via 24 tools | v1.16.2 |

## Get Started in 5 Minutes

```bash
pip install cks-core cks-runtime cks-mcp
```

Then connect to Claude Desktop – see the [Quick Start guide](quickstart.md).

For a deeper dive into the MCP server specifically: its
[24 tools](cks-mcp/tools/index.md), [security model](cks-mcp/security.md),
and [architecture](cks-mcp/architecture/ARCHITECTURE.md) each have their
own page under [cks-mcp](cks-mcp/index.md).

---

## Why CKS?

Today, the same knowledge exists in many incompatible forms – documents, databases, JSON, source code, AI prompts. CKS separates **knowledge itself** from every representation. Representations may change, but canonical knowledge remains the same.
