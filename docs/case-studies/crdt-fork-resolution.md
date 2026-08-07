# Case Study: Automatic CRDT Fork Resolution with Fork Agent

**Problem:** When two replicas of cks-mcp concurrently modify the same
knowledge object (e.g. via gossip), a CRDT conflict (fork) arises.
Without automatic resolution, the conflict remains unresolved, leaving
the graph in an inconsistent state and requiring manual intervention.

**CKS solution:** CRDT adapter (ADR-013) Stages 2–3: MV-Register,
causality tracking, fork detection events, and a dedicated
`ForkResolutionAgent` that autonomously claims and resolves
`crdt_fork` tasks from the persistent outbox.

---

## Scenario

We run two instances of cks-mcp (on ports 8765 and 8766) sharing
knowledge via gossip, backed by SQLite databases `/tmp/cks-a.db` and
`/tmp/cks-b.db`. A session with a single object `concept-1` is created
on instance A. Then a conflicting update is applied on instance B.
Gossip synchronises the sessions, and the CRDT layer detects a fork in
the MV-Register.

---

## Tools Used

- `validate_knowledge` / `evolve_knowledge` – creating and modifying the session.
- `cks-fork-agent` – standalone process that resolves CRDT forks.
- SQLite introspection – verifying MV-Register state.

---

## What Happened

1. **Session creation** – Instance A received a `concept-1` with
   description "Initial version".
2. **Conflicting update** – Instance B independently updated the same
   object to "Version from instance B" without coordinating with A.
3. **Gossip synchronisation** – After gossip rounds, both replicas
   contained both versions of the object.
4. **CRDT fork detection** – The CRDT layer detected two concurrent
   pointers for `concept-1` in `cks_mv_register` and escalated a
   `CRDTForkDetected` event.
5. **Outbox task creation** – A `crdt_fork` task was written to the
   persistent outbox (`cks_outbox_tasks`).
6. **Fork Agent resolution** – `cks-fork-agent` (polling every 10 s)
   claimed the task, applied its resolution policy (causality →
   most‑recent → alphabetical tie‑break), and called
   `resolve_pointer`, collapsing the MV-Register to a single winner.
7. **Verification** – `SELECT * FROM cks_mv_register WHERE pointer_key =
   'concept-1'` returned exactly one row; the outbox task status was
   `COMPLETED`.

Log excerpt:
```
[cks-fork-agent] resolved crdt_fork task_id=3 pointer_key=concept-1
```

---

## Key Takeaways

- **CRDT fork resolution works end‑to‑end.** The agent correctly
  consumes outbox tasks, resolves forks, and updates the MV-Register.
- **Fully autonomous.** No human intervention was required after the
  initial session creation and conflicting update.
- **Persistent outbox ensures reliability.** If the agent crashes
  mid‑resolution, another instance can claim the task.
- **Integration with gossip is functional** (verified in a separate
  setup). The CRDT quarantine, Merkle tree, and causality checks all
  performed as designed.

---

## Current Limitations

- `OutboxEmbeddingWorker` raises `'AddObject' object has no attribute
  'object_id'` in certain background tasks – tracked as a known bug
  (see issue #...).
- CRDT objects are only populated during gossip exchange, not on
  local `evolve_knowledge` calls – this is by design (ADR-013 Stage 2)
  but means the fork agent cannot resolve conflicts that originate
  purely within a single node.
- Gossip synchronisation itself requires careful ordering of startup
  and occasional manual restart – stability improvements are planned.

---

## Reproduce It Yourself

1. Start two cks-mcp instances with gossip enabled on different ports
   and separate SQLite databases (see `scripts/` folder for helper
   scripts).
2. Create a session on instance A with `validate_knowledge`.
3. Apply a conflicting update on instance B with `evolve_knowledge`.
4. Wait for gossip rounds (or manually trigger sync).
5. Inspect `cks_mv_register` – two rows should appear.
6. Start `cks-fork-agent --poll-interval 10` pointing at one of the
   databases.
7. Verify that after ~10–20 seconds only one row remains and the
   outbox task is marked `COMPLETED`.