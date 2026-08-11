# ADR-001: AI Assistant Chat Panel

**Status:** Proposed
**Related:** cks-mcp ADR-007 (CKSAgentOrchestrator — a different, longer-running
multi-agent pipeline; this ADR is a single interactive chat turn, not that
pipeline), cks-mcp ADR-009/ADR-010 (Sweeper/Process Control Tools — the
pattern this ADR follows: thin cks-mcp-side tool, cks-studio-side UI),
companion cks-mcp ADR-011 (`ai_chat` Tool — owns the agentic loop and
provider contract this ADR consumes)

## Context

Right now a human drives cks-studio (mouse, forms, the graph canvas) while
an LLM drives the same knowledge graph through Claude Desktop, over a
completely separate stdio connection to `cks-mcp`. Three consequences of
that split, already written up in the "Сделать студию единой средой"
proposal:

1. Two disconnected interfaces — switching between "watch the graph" and
   "instruct the AI" is the debugging loop's main friction point.
2. The AI's actions are invisible until a human manually refreshes the
   studio and reconnects the session — no live feedback.
3. There is no shared conversation the human can see, correct, or build on
   — every AI interaction starts from zero context about what's currently
   on the canvas.

The Agent Panel work just shipped (Start/Stop/Request Stop for sweepers
and standalone processes) was about controlling *background* agents that
already run inside `cks-mcp`. This ADR is a different thing: an
interactive, synchronous chat turn where a human types a prompt, an LLM
decides which of `cks-mcp`'s ~60 tools to call, and the graph updates
live in the same window. It reuses the read side (`useSessionStore`,
`useGraphStore`, `getFullGraph`) the Agent Panel and Graph page already
share, but needs one new piece of server-side machinery that doesn't
exist yet: a tool-calling (agentic) loop over the Anthropic API.

## Decision

### 1. The chat loop lives in `cks-mcp`, not in the browser

`cks-studio` stays a thin client — same principle the original proposal
already lands on, and the same shape as every other page in this
codebase: `mcpTools.ts` calls a tool over `POST /mcp`, gets JSON back,
renders it. Concretely:

- **New MCP tool `ai_chat`** in `cks-mcp` (companion ADR-011 owns the
  server-side design in full: provider selection, loop bounds, tool
  allowlist). `cks-studio` calls it exactly like it calls `evolve_knowledge`
  or `start_agent` today — through the existing `callTool()` in
  `mcpClient.ts`. No new transport, no API key ever reaches the browser.
- The alternative — calling `api.anthropic.com` directly from
  `cks-studio` — was rejected outright: it would put an Anthropic API key
  in browser-shipped JS, and it would mean reimplementing the tool
  dispatch loop (calling `evolve_knowledge`, `query_subgraph`, etc.) a
  second time on the frontend, in a different language, against the same
  `Runtime` object `cks-mcp` already holds server-side. `cks-mcp` already
  has this dispatch table (`registry.py`'s `TOOLS` dict) in-process —
  reusing it means the LLM's tool calls execute as direct Python calls
  against the live `Runtime`, not a second round-trip through the same
  HTTP endpoint the LLM's own request just came in on.

### 2. Conversation history is stateless and lives in `cks-studio`, not in a new server-side table

`ai_chat` takes the *entire* message history as an argument on every
call (`messages: ChatMessage[]`) and returns the assistant's turn plus
whatever tool calls it made — the server holds no session-scoped chat
state between calls. `cks-studio` keeps the array in a zustand store
(mirroring `useSessionStore`/`useGraphStore`, not component-local
`useState`, since — like session/graph state — a page switch shouldn't
lose the conversation) and passes it back on the next turn.

This was chosen over a new `cks_chat_history` table in cks-runtime for
one reason: chat turns aren't Knowledge Structure — they don't belong in
the CRDT graph, they don't need CRDT merge semantics, and they don't need
to survive a `cks-mcp` restart the way a sweeper's `desired_running` flag
does. If a durable, resumable chat history becomes a real requirement
(multi-device continuation, audit trail across sessions) that's a
follow-up ADR with its own storage design — not a reason to block this
one on a schema decision.

### 3. Every LLM-initiated tool call is pinned to the chat's `session_id`

`ai_chat(session_id, messages, ...)` requires `session_id` the same way
`evolve_knowledge` and `query_subgraph` already do. Before executing any
tool call the LLM requests, the server-side loop **overwrites** that
call's `session_id`/`session-shaped` argument with the one `ai_chat` was
given, rather than trusting whatever the LLM put there (companion
ADR-011 §3 has the full argument-injection rule, including which field
name to override per tool). This isn't a hypothetical: the whole point
of exposing `evolve_knowledge` to the LLM is letting it write to a graph,
so a prompt-injected or simply confused LLM call that names a *different*
session_id must not be able to mutate a graph the chat's own session_id
doesn't point at. The human is looking at one graph, in one browser tab,
connected to one session — the chat cannot be a side channel to any other
one.

### 4. The chat panel is a new page, not a sidebar on the Graph page

Given `useSessionStore`/`useGraphStore` are already app-wide zustand
stores (not `GraphPage`-local state — see `sessionStore.ts`'s own doc
comment on why that migration happened), a chat panel doesn't need to be
physically embedded in `GraphPage` to see and mutate the same graph. It's
added as `/chat` in `App.tsx`'s existing `NavBar`/`Routes` pattern (same
as `/agents` was), which keeps `GraphPage` itself unchanged and lets the
human keep the Graph tab open in one window and Chat in another if their
workflow wants that split — the shared store makes both views consistent
regardless of which one is currently mounted.

Later iteration (explicitly out of scope for this ADR) can add a
picture-in-picture / split-pane mode that renders `GraphCanvas` and
`ChatPanel` side by side on one route; the store design here doesn't
block that.

### 5. Graph refresh after a chat turn reuses the existing full-refetch path, not a diff-apply

When `ai_chat`'s response includes one or more tool calls that mutated
the graph (`evolve_knowledge`, `revert_version`, `merge_branch`, ...),
the chat panel calls the same `getFullGraph(sessionId)` +
`useGraphStore.setNodes/setEdges` sequence `GraphPage.handleConnect`
already runs today, rather than trying to translate each individual tool
result into an incremental store patch (the way `useEvolveMutation`'s
*optimistic* single-operation path does for a human-submitted form).

Rejected alternative: incremental patching per tool call, mirroring
`useEvolveMutation`'s optimistic-update/rollback dance. Rejected for v1
because the LLM's tool calls are heterogeneous (an `evolve_knowledge`
add, a `revert_version`, a `merge_branch` are shaped completely
differently) and a chat turn commits server-side *before* the studio
ever sees it — there's no "optimistic" window to protect the way there
is for a human's in-flight form submission, so the complexity of a
per-tool patcher buys nothing here. A full refetch after the turn
completes is simpler and already proven correct; revisit only if
refetch latency becomes a measured problem on large graphs.

### 6. Tool-call transparency: show what the LLM did, not just what it said

Each assistant turn in the chat renders as: the LLM's natural-language
reply, plus a collapsed-by-default list of tool calls it made this turn
(tool name, a short argument summary, success/error). This is a direct
requirement from the original proposal ("ошибки и предупреждения от ИИ
видны в том же чате") and mirrors `AgentPanel`'s existing
`actionError`-under-the-card convention — errors surface inline, next to
the thing that failed, not as a toast that's gone by the time you look.

## Consequences

**Positive:**
- No new persistent storage, no new cks-runtime schema — the entire
  feature is one new MCP tool plus one new page, following the same
  thin-client shape every other cks-studio page already uses.
- `session_id` pinning (Decision 3) means the chat cannot be used to
  reach outside the graph the human is currently looking at, regardless
  of what the LLM is told or tricked into requesting.
- Reuses `useSessionStore`/`useGraphStore` as-is — no prop drilling, no
  new context provider, and the Graph tab and Chat tab are automatically
  consistent with each other.

**Negative / accepted tradeoffs:**
- Stateless chat history (Decision 2) means refreshing the browser tab
  loses the conversation (graph state does not persist across a
  `cks-studio` reload either, for the same reason today — session_id has
  to be re-entered — so this matches existing behavior rather than
  regressing it). A "resume chat" feature is explicitly deferred.
- Full-refetch-after-turn (Decision 5) means a chat turn's graph update
  is not visible until the *entire* turn (potentially several tool
  calls) completes — no partial/streaming graph updates in v1. Streaming
  UI (SSE) is deferred to Milestone 2 of the companion cks-mcp ADR-011.
- The MVP requires `ANTHROPIC_API_KEY` (companion ADR-011 §4) — no local
  Ollama path for tool-calling in v1, unlike `construct_knowledge`'s
  provider auto-selection. Documented explicitly in the Settings page so
  it isn't a silent surprise when Ollama-only deployments hit the Chat
  tab.

## Implementation Plan

### Milestone 1 — MVP: one-shot chat, full-refetch, no streaming

**cks-mcp side** (full design in companion ADR-011; summarized here for
the plan to read end to end):

```python
# src/cks_mcp/tools/ai_chat/schema.py
AI_CHAT_SCHEMA = {
    "name": "ai_chat",
    "description": (
        "Send a chat turn to an LLM with access to a restricted set of "
        "cks-mcp tools, scoped to 'session_id'. The LLM may call tools "
        "(query_subgraph, evolve_knowledge, ...); this handler executes "
        "them server-side and feeds results back to the LLM until it "
        "produces a final text reply or the iteration cap is hit. Every "
        "tool call the LLM makes has its session-shaped argument "
        "overwritten with 'session_id' before execution -- the LLM "
        "cannot target a different session (see cks-mcp ADR-011 §3). "
        "Returns {'reply': str, 'tool_calls': [...], 'messages': [...]} "
        "-- 'messages' is the full updated history; pass it back as-is "
        "on the next turn (this tool is stateless between calls)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "messages": {
                "type": "array",
                "description": "Full conversation so far, including the "
                "new user turn. Empty/omitted 'messages' plus a 'prompt' "
                "starts a fresh conversation.",
            },
            "prompt": {
                "type": "string",
                "description": "Shorthand for starting a new conversation "
                "with a single user message; ignored if 'messages' is set.",
            },
        },
        "required": ["session_id"],
    },
}
```

```python
# src/cks_mcp/tools/ai_chat/handler.py
from __future__ import annotations

import json
from typing import Any

from cks_mcp.llm_providers import call_anthropic_with_tools  # new, see ADR-011
from cks_mcp.registry import TOOLS
from cks_runtime.runtime import Runtime

# Denylist, not allowlist: anything that manages the server/runtime itself
# (storage migration, plugin/process lifecycle, backup/restore) is never
# something a chat LLM should be able to invoke, no matter the prompt.
_DISALLOWED_TOOLS = {
    "migrate_storage", "export_storage", "import_storage",
    "list_plugins", "start_agent", "stop_agent", "request_process_stop",
    "register_graph",  # writes to the public gallery -- human-only for v1
}
_MAX_ITERATIONS = 8

# Tools whose arguments are session-scoped and must be pinned to the
# ai_chat caller's session_id before execution (see ADR §3).
_SESSION_ARG_NAME = "session_id"


def _tool_specs_for_llm() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": tool["description"],
            "input_schema": tool["inputSchema"],
        }
        for name, tool in TOOLS.items()
        if name not in _DISALLOWED_TOOLS and name != "ai_chat"
    ]


async def ai_chat(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    session_id = arguments["session_id"]
    messages: list[dict[str, Any]] = list(arguments.get("messages") or [])
    if not messages:
        messages = [{"role": "user", "content": arguments["prompt"]}]

    tool_specs = _tool_specs_for_llm()
    executed_calls: list[dict[str, Any]] = []

    for _ in range(_MAX_ITERATIONS):
        response = await call_anthropic_with_tools(
            messages=messages, tools=tool_specs,
        )
        messages.append({"role": "assistant", "content": response["content"]})

        tool_use_blocks = [b for b in response["content"] if b["type"] == "tool_use"]
        if not tool_use_blocks:
            reply = "".join(
                b["text"] for b in response["content"] if b["type"] == "text"
            )
            return {"reply": reply, "tool_calls": executed_calls, "messages": messages}

        tool_results = []
        for block in tool_use_blocks:
            tool_name = block["name"]
            tool_args = dict(block["input"])
            if _SESSION_ARG_NAME in TOOLS[tool_name]["inputSchema"]["properties"]:
                tool_args[_SESSION_ARG_NAME] = session_id  # pin, ADR §3

            handler = TOOLS[tool_name]["handler"]
            try:
                result = await handler(runtime, tool_args)
                is_error = False
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc) or "An internal error occurred."}
                is_error = True

            executed_calls.append(
                {"name": tool_name, "arguments": tool_args, "result": result, "is_error": is_error}
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                    "is_error": is_error,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return {
        "reply": "Reached the tool-call iteration limit without a final answer.",
        "tool_calls": executed_calls,
        "messages": messages,
    }
```

Then wire it into `registry.py` next to the other tools, same pattern as
every existing entry (`from cks_mcp.tools.ai_chat import ai_chat`,
`from cks_mcp.tools.ai_chat.schema import AI_CHAT_SCHEMA`, add to `TOOLS`).

**cks-studio side:**

```typescript
// src/services/mcpTools.ts — append

export interface ChatMessage {
  role: 'user' | 'assistant'
  /** String for plain turns; block array when it carries tool_use/tool_result
   *  content (mirrors the Anthropic Messages API content shape 1:1, since
   *  it's round-tripped through ai_chat's 'messages' as-is — see ADR-001 §2). */
  content: string | Record<string, unknown>[]
}

export interface ExecutedToolCall {
  name: string
  arguments: Record<string, unknown>
  result: Record<string, unknown>
  is_error: boolean
}

export interface AiChatResult {
  reply: string
  tool_calls: ExecutedToolCall[]
  messages: ChatMessage[]
}

/** Names of tools whose successful execution means the graph may have
 *  changed and the canvas should be refetched (see ADR-001 §5). Kept in
 *  sync manually with cks-mcp's graph-mutating tool set -- there's no
 *  tool-metadata flag for this yet, so this is the same kind of small,
 *  explicit constant AgentPanel's PROCESS_KINDS-style lists already are
 *  elsewhere in this codebase. */
const GRAPH_MUTATING_TOOLS = new Set([
  'evolve_knowledge',
  'revert_version',
  'merge_branch',
  'merge_knowledge',
  'resolve_contradiction',
  'resolve_temporal_conflict',
  'resolve_gossip_conflict',
  'refresh_verification',
])

export function toolCallsMutatedGraph(calls: ExecutedToolCall[]): boolean {
  return calls.some((c) => !c.is_error && GRAPH_MUTATING_TOOLS.has(c.name))
}

export async function aiChat(
  sessionId: string,
  messages: ChatMessage[],
): Promise<AiChatResult> {
  const result = await callTool('ai_chat', { session_id: sessionId, messages })
  return result as unknown as AiChatResult
}
```

```typescript
// src/features/ai-chat/chatStore.ts — new zustand store, same shape as
// sessionStore.ts/graphExplorerStore.ts (module-level state, not
// component-local, so switching pages doesn't lose the conversation)

import { create } from 'zustand'
import type { ChatMessage, ExecutedToolCall } from '@/services/mcpTools'

interface ChatTurn {
  role: 'user' | 'assistant'
  text: string
  toolCalls?: ExecutedToolCall[]
}

interface ChatState {
  turns: ChatTurn[]
  rawMessages: ChatMessage[]  // passed back to ai_chat verbatim each call
  isSending: boolean
  error: string | null
  appendUserTurn: (text: string) => void
  appendAssistantTurn: (text: string, toolCalls: ExecutedToolCall[], rawMessages: ChatMessage[]) => void
  setSending: (v: boolean) => void
  setError: (e: string | null) => void
  reset: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  turns: [],
  rawMessages: [],
  isSending: false,
  error: null,
  appendUserTurn: (text) =>
    set((s) => ({
      turns: [...s.turns, { role: 'user', text }],
      rawMessages: [...s.rawMessages, { role: 'user', content: text }],
    })),
  appendAssistantTurn: (text, toolCalls, rawMessages) =>
    set((s) => ({
      turns: [...s.turns, { role: 'assistant', text, toolCalls }],
      rawMessages,
    })),
  setSending: (v) => set({ isSending: v }),
  setError: (e) => set({ error: e }),
  reset: () => set({ turns: [], rawMessages: [], error: null }),
}))
```

```typescript
// src/features/ai-chat/useAiChat.ts

import { useSessionStore } from '@/services/sessionStore'
import { aiChat, getFullGraph, toolCallsMutatedGraph } from '@/services/mcpTools'
import { useGraphStore } from '@/features/graph-explorer/graphExplorerStore'
import { cksToReactFlow } from '@/shared/utils/graphUtils'
import { useCallback } from 'react'
import { useChatStore } from './chatStore'

export function useAiChat() {
  const sessionId = useSessionStore((s) => s.sessionId)
  const { turns, rawMessages, isSending, error, appendUserTurn, appendAssistantTurn, setSending, setError } =
    useChatStore()
  const setNodes = useGraphStore((s) => s.setNodes)
  const setEdges = useGraphStore((s) => s.setEdges)

  const send = useCallback(
    async (text: string) => {
      if (!sessionId.trim()) {
        setError('No active session — connect to a session on the Graph tab first.')
        return
      }
      appendUserTurn(text)
      setSending(true)
      setError(null)
      try {
        const pendingMessages = [...rawMessages, { role: 'user' as const, content: text }]
        const result = await aiChat(sessionId, pendingMessages)
        appendAssistantTurn(result.reply, result.tool_calls, result.messages)

        // Same full-refetch path GraphPage.handleConnect already uses —
        // see ADR-001 §5 for why this isn't an incremental patch.
        if (toolCallsMutatedGraph(result.tool_calls)) {
          const subgraph = await getFullGraph(sessionId)
          const { nodes, edges } = cksToReactFlow(subgraph)
          setNodes(nodes)
          setEdges(edges)
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Network error')
      } finally {
        setSending(false)
      }
    },
    [sessionId, rawMessages, appendUserTurn, appendAssistantTurn, setSending, setError, setNodes, setEdges],
  )

  return { turns, isSending, error, send }
}
```

`ChatPanel.tsx`/`ChatsPage.tsx` follow `AgentPanel.tsx`/`AgentsPage.tsx`'s
exact split (dumb presentational panel + thin page wrapper), rendering
`turns` as a scrollback with a text input pinned to the bottom, each
assistant turn showing `toolCalls` the same way `AgentCard` shows
`actionError` today — small, inline, not a modal. Wire `/chat` into
`App.tsx`'s `NavBar`/`Routes` next to `/agents`.

**Acceptance for Milestone 1:** a human on the Graph tab can switch to
Chat, type "add a Person node named Ada Lovelace and connect her to the
Analytical Engine with a designed relation", see the tool calls the LLM
made, and see the new node/edge appear on the Graph tab's canvas without
a manual reconnect.

### Milestone 2 — streaming + Ollama tool-calling

- Add an SSE variant of `POST /mcp` (or a dedicated `/mcp/stream`
  endpoint) so `ai_chat` can push assistant text tokens and
  `tool_call_started`/`tool_call_completed` events as they happen,
  instead of the studio blocking on one long request. `ChatPanel`
  switches from `await aiChat(...)` to consuming an `EventSource`.
- Extend `llm_providers.py` with an Ollama tool-calling path (`/api/chat`
  with a `tools` array, distinct from the `/api/generate` endpoint
  `construct_knowledge` uses today) so `ai_chat` can participate in the
  existing `CKS_LLM_PROVIDER=auto` selection instead of hard-requiring
  `ANTHROPIC_API_KEY`.

### Milestone 3 — durable, resumable conversations

- Only if real usage shows the stateless-history tradeoff (Decision 2)
  actually hurts: a `cks_chat_history` table (own cks-runtime ADR, same
  split this feature has followed throughout — schema/persistence in
  cks-runtime, tool contract in cks-mcp) keyed by `session_id`, so
  reloading `cks-studio` or switching machines can resume a
  conversation rather than starting over.
