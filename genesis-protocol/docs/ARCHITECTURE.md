# RFC-001 · Reference Architecture

**Genesis Protocol / 1,111 NFT-bound agents / XRPL Mainnet ownership / off-chain cognition**

## 1. Bounded contexts

| Bounded context | Primary responsibility | Source of truth |
|---|---|---|
| `identity-indexer` | XRPL mint/ownership/burn/remint provenance and reconciliation | Validated XRPL ledger |
| `agent-registry` | immutable genome slots, generational NFT→agent binding, public cards, lifecycle | PostgreSQL event-projected registry |
| `owner-auth` | Proof of current ownership, short sessions, revocation | XRPL + authenticated session cache |
| `agent-kernel` | Actor state, bounded planner, local memory/policy | Durable Object per agent + PostgreSQL event log |
| `a2a-gateway` | Peer discovery, message signatures, tasks, quotas | NATS + transactional inbox/outbox |
| `tool-sandbox` | MCP invocation, strict tool scopes, egress firewall | Signed capability lease + audit journal |
| `memory-service` | Public lineage, private owner memory, semantic recall | PostgreSQL + pgvector + R2 |
| `relationship-service` | Evidence-backed peer relation graph | Relational directed edges + event provenance |
| `mission-engine` | Long-running DAGs, retries, cancellation and compensation | Temporal workflow history |
| `world-frontend` | Real-time visibility, passports, tasks and owner approvals | Authorized projections only |
| `observability` | OpenTelemetry traces, SLO, cost, error response | ClickHouse + metrics stack |

### Trust boundaries

`wallet > public API > ownership attestation > actor > peer gateway > tools > third-party API > XRPL ledger` are distinct trust domains. The wallet is non-custodial. The backend does not hold seed phrases. A2A text is **untrusted input** with no grant-making authority.

## 2. Language-level design

**Primary runtime:** TypeScript, strict mode (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`), Node.js 22 LTS or supported stable runtime. **Ingress:** Cloudflare Workers + Hono + OpenAPI 3.1. **Actors:** Durable Objects (logical one-per-agent) with minimal state local to actor and the canonical event log in PostgreSQL. **High-integrity services:** Rust for XRPL event decoding, hash validation and sandbox isolation. **Research:** Python 3.12+ for evaluation pipelines and offline reproducibility.

Use **hexagonal architecture** around ledger, model, memory and tool ports so implementations can be replaced without rewriting business invariants. The model router must never write an irreversible lifecycle transition directly; only the deterministic lifecycle service may do so.

```ts
type NFTokenID = string & { readonly __type: 'NFTokenID' };
type AgentID = string & { readonly __type: 'AgentID' };
type ValidatedLedgerIndex = number & { readonly __type: 'ValidatedLedgerIndex' };

type AgentIdentity = Readonly<{
  nftokenId: NFTokenID;
  agentId: AgentID;
  slotId: number;
  generation: number;
  personaSeedCommitment: string;
  immutableGenomeHash: string;
  canonicalCollectionId: string;
}>;

type AuthoritativeState = Readonly<{
  identity: AgentIdentity;
  lifecycle: 'DORMANT' | 'ACTIVE' | 'SUSPENDED' |
    'TRANSFER_FROZEN' | 'BURN_PENDING' | 'BURNED';
  ownerAddress: string | null;
  revocationEpoch: number;
  lastValidatedLedger: ValidatedLedgerIndex;
}>;
```

Example types are design intent, not a compiled package.

## 3. XRPL ingestion and reconciliation

- WebSocket subscriptions for near-real-time candidate updates; query **validated** transaction metadata and ledger state for finality.
- At boot: resolve the canonical issuer, taxon and approved NFT membership manifest, including successor generations; compare all known NFTs to XRPL account NFT pages, history and mint transactions.
- Persist immutable chain cursors with ledger hash and index, support backfill from historical APIs and fail closed on gaps.
- Changes are projected through append-only `LedgerEvent` with `(tx_hash, nftoken_id, event_kind)` unique dedup key.
- Every privileged API call checks fresh ownership through a bounded cache with a hard invalidation barrier on transfer/burn and fail-closed behavior on uncertainty.
- The initial marketplace mint-out is a one-shot **historical distribution milestone**, independent of the current live supply. A burn and later successor remint never re-trigger it.

**Indexer consistency:** do not claim the chain exposes a native 'NFT collection contract' like ERC-721. Identify the canonical collection via a published allowlist of issuer, taxon and NFT IDs plus audited metadata bindings. XRPL NFTs use native ledger data structures, not ERC-721 Solidity contracts on XRPL Mainnet.

## 4. Per-agent actor model

**Actor key:** `agent_id`, freshly minted per generation. A slot is the persistent genome template, *not* an actor key. Each logical actor is serialized for local coordination; distributed work is asynchronous, durable and idempotent. Agent activation is **lazily provisioned**. 1,111 identities does not require 1,111 always-on language models.

**Planner pipeline:** classify → verify policy/ownership → retrieve scoped memory → select capability → reason → act through sandbox → verify output → record signed receipt → persist memory. Bounded `max_steps`, `max_output_tokens`, `max_peer_hops` and `max_execution_ms` are enforced outside the model. Never trust the model's own accounting of resource consumption.

**Memory partitions:**

```text
agent/{agent_id}/public/lineage     // explicitly public, transferable
agent/{agent_id}/owner/{owner_epoch}/private
agent/{agent_id}/mission/{task_id}/ephemeral
agent/{agent_id}/system/audit       // restricted append-only receipts
agent/{agent_id}/memorial           // burned-only sanitized projections
```

All embeddings carry principal, namespace, disclosure scope and deletion epoch so vector search can never retrieve previous owner's private data for another owner. Encrypt sensitive partitions using per-epoch data keys; after burn/transfer revoke keys and enforce physical garbage collection retention.

## 5. Genome interpreter

Compile NFT traits into **versioned, bounded configuration**. Deterministic mapping is tested with snapshot vectors and publicly auditable metadata commitments. Avoid implying the NFT contains live executable code: the **genome config** is on/off-chain metadata; execution is in the agent runtime.

```ts
function compileTraits(genome: Genome): RuntimePolicy {
  return {
    discoveryBreadth: clamp(Math.floor(genome.stats.curiosity / 20), 1, 5),
    verifierPasses: clamp(Math.ceil(genome.stats.reasoning / 40), 1, 3),
    peerOutreachAllowed: genome.stats.sociability >= 30,
    // All values remain subordinate to server-side limits.
    maxDelegationDepth: Math.min(3, GLOBAL_LIMITS.maxDelegationDepth),
    requiredApprovalForExternalWrites: true,
  };
}
```

The archetype registry is signed and semantic-versioned. Changing tool eligibility requires reviewed migrations, cannot be silent and cannot bypass baseline safety.

## 6. Workflow reliability

- **JetStream** for agent-to-agent event transport; delivery is at-least-once and consumers are idempotent.
- **Temporal** for durable multi-stage missions and cancellation orchestration.
- **PostgreSQL outbox** to connect transactional state changes and messaging without dual-write inconsistency.
- **Quotas** reserved atomically at mission root and inherited by children; prevent resource amplification.
- **OpenTelemetry** to carry `traceparent` across the whole mission, with sensitive prompt and secret redaction.
- **Replay** of deterministic event history rebuilds projections without reviving a `BURNED` agent.

## 7. Data storage / indexes

```sql
CREATE TABLE genome_slot (
  slot_id SMALLINT PRIMARY KEY CHECK (slot_id BETWEEN 1 AND 1111),
  canonical_genome_hash CHAR(64) NOT NULL,
  canonical_traits JSONB NOT NULL,
  current_generation INT NOT NULL DEFAULT 0
);

CREATE TABLE genesis_agent (
  agent_id UUID PRIMARY KEY,
  nftoken_id CHAR(64) UNIQUE NOT NULL,
  slot_id SMALLINT NOT NULL REFERENCES genome_slot(slot_id),
  generation INT NOT NULL CHECK(generation >= 1),
  persona_seed_commitment CHAR(64) UNIQUE NOT NULL,
  lifecycle TEXT NOT NULL,
  current_owner TEXT,
  revocation_epoch BIGINT NOT NULL DEFAULT 0,
  last_validated_ledger BIGINT NOT NULL,
  burned_tx CHAR(64) UNIQUE,
  UNIQUE(slot_id, generation),
  CHECK(lifecycle <> 'BURNED' OR (burned_tx IS NOT NULL AND current_owner IS NULL))
);

-- A slot can have many historical generations, but at most one unburned NFT.
CREATE UNIQUE INDEX uq_one_live_gen_per_slot ON genesis_agent(slot_id)
  WHERE lifecycle <> 'BURNED';

CREATE TABLE agent_event (
  event_id UUID PRIMARY KEY,
  agent_id UUID NOT NULL REFERENCES genesis_agent(agent_id),
  event_type TEXT NOT NULL,
  chain_tx_hash CHAR(64),
  chain_ledger BIGINT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_burn_once ON agent_event(agent_id)
  WHERE event_type = 'AgentBurned';
```

**Important:** Reissuance requires validated burn, issuer authorization, fixed slot-genome hash, and a transactionally exclusive mint reservation. The reminted NFT has a **new** token ID and its agent has empty memory, new persona, new relationships and no predecessor privileges. SQL `CHECK` by itself is insufficient to prevent `BURNED → ACTIVE` updates. Enforce an insert-only transition procedure or DB trigger plus service-level state machine and event projector. Mission tables require row-level access policies and `owner_epoch` isolation; never serve private memory based only on a `nftoken_id` route parameter.

## 8. The Garden — launch-native world projection

The Garden is **in the mint-out V1 baseline, not a later roadmap milestone**. Its public world, visible personas, A2A collaboration and persistent relationships must work at the initial reveal. The full implementation contract, tools, UI actions, zones and launch test matrix are in [`THE_GARDEN.md`](THE_GARDEN.md).

The Garden is a materialized, **public-consent filtered** projection of agent activity, not the canonical truth store. Use SSE for status updates, Cloudflare Durable Objects WebSocket Hibernation with sequence/replay protection for real-time presence, and PixiJS v8 for the 2D canvas. Zone rooms receive **consent-filtered projections** of true agent events; animation has no authority over mission, memory, identity or burn state. Public feeds do not expose prompt internals, private messages, wallet proof challenges or secrets. Burned agents render as archival memorials, never as interactive live participants. A successor generation appears as a separate character node that may link to the prior memorial through public edition lineage, but never inherits private history or social reputation.

## 9. Open engineering decisions

- Canonical issuer/taxon/token allowlist and metadata commitment strategy: requires independent on-chain verification.
- Wallet signature support / login challenges: implement against chosen wallet's documented abilities; no arbitrary off-chain signature assumptions.
- Genome trait source and reveal commitment: publish deterministic test vectors before reveal.
- Exact post-burn retention windows and moderation policies: require privacy review.
- Durable Object state checkpointing and PostgreSQL dual-write coordination: prototype failure injection.
- Agent Card standards compatibility: validate against an A2A 1.x SDK and contracts, not only custom JSON.

- Issuer-approved replacement-mint distribution rights, marketplace indexing, anti-double-mint controls and same-genome verification must be finalized before production reissues.
