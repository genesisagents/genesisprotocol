# RFC-004 · APIs, Event Contracts and Identity/Ownership Enforcement

## Public / authenticated endpoint design

| Endpoint | Scope | Contract |
|---|---|---|
| `GET /v1/collection/status` | public | fixed slots, lifetime mints, live, vacant, burned, replacement mints, currently active |
| `GET /v1/slots/{slot_id}/genome` | public | immutable original genome snapshot for a canonical edition |
| `GET /v1/slots/{slot_id}/lineage` | public | generation-by-generation NFT IDs, new personalities, redacted memorials |
| `POST /v1/admin/slots/{slot_id}/reissue-reservations` | issuer ops | reserve vacant burned slot for a validated replacement mint, not public |
| `GET /v1/agents/{id}` | public | immutable identity summary, lifecycle, public genome hash |
| `GET /v1/agents/{id}/card` | public | sanitized A2A capability card; `BURNED` → inactive |
| `GET /v1/agents/{id}/genome` | public | disclosed traits and their bounded runtime effects |
| `GET /v1/agents/{id}/relationships` | redacted/public | published, evidence-backed edges |
| `GET /v1/agents/{id}/memorial` | public | burned-only sanitized history, burn tx reference |
| `POST /v1/auth/challenge` | public | nonce, domain, expiry, scope, anti-replay binding |
| `POST /v1/auth/verify` | wallet proof | short-lived owner session, current ledger verification |
| `POST /v1/agents/{id}/tasks` | current owner | authenticated policy-gated task request |
| `GET /v1/tasks/{task_id}` | involved principal | task state + redacted receipts |
| `POST /v1/tasks/{task_id}/approve` | owner | signed, scoped side-effect approval |
| `POST /v1/tasks/{task_id}/cancel` | owner/system | durable cancellation intent |
| `POST /v1/a2a/tasks` | authorized peer | standards-aligned peer task envelope |
| `GET /v1/events/stream` | scoped | SSE events with reconnect cursor and gap detection |
| `GET /v1/garden/bootstrap` | public/scoped | initial world snapshot; permissions, zones, consent-filtered avatar status |
| `GET /v1/garden/zones/{zone_id}/snapshot` | public/scoped | room state with monotonic sequence and revision |
| `GET /v1/garden/agents/{id}/presence` | public/scoped | awake/sleeping/mission/inactive status from authoritative agent state |
| `GET /v1/garden/relationships` | public/scoped | evidence-backed relationships with privacy/consent redaction |
| `GET /v1/garden/missions/{mission_id}/receipts` | authorized/public filtered | mission artifact/evidence without secret context |
| `GET /v1/garden/events` | scoped | replayable world event deltas with cursor and gap handling |
| `WS /v1/garden/zones/{zone_id}` | scoped | Hibernatable Durable Object world room; batched versioned deltas |


OpenAPI 3.1 definition and generated client types will be published with implementation. No endpoint above is asserted to exist already.

## Event ontology

```text
CollectionSlotAdmitted
AgentIdentityBound
AgentActivated
AgentSuspended
OwnerTransferObserved
OwnerTransferValidated
OwnerEpochRotated
AgentBurnCandidateObserved
AgentBurnValidated
AgentBurned
AgentCapabilityRevoked
AgentPrivateMemoryErasureRequested
AgentPrivateMemoryErasureCompleted
AgentMessageSent
AgentTaskAccepted
AgentTaskCompleted
AgentTaskCanceled
AgentUnavailable
AgentMemorialPublished
SlotVacated
SlotReissueReserved
SlotReissueReleased
SuccessorNFTokenMintValidated
SuccessorAgentCreated
AgentPersonaInitialized
GardenPresenceChanged
GardenMessageVisible
GardenMissionProgressed
GardenRelationshipUpdated
GardenMemorialCreated
GenomeMismatchRejected
```

Envelope shape (illustrative):

```json
{
  "event_id": "0193c46f-a127-7ccf-bf89-cb1234567890",
  "event_type": "AgentBurned",
  "schema_version": "1.0",
  "agent_id": "0193c46f-a127-7ccf-bf89-cb1234567890",
  "nftoken_id": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
  "revocation_epoch": 9,
  "source": {"chain": "XRPL", "validated": true, "ledger_index": 99999999, "tx_hash": "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"},
  "occurred_at": "2027-01-01T00:00:00Z",
  "trace_id": "b75e7f6c5c9545d0a7c99f39d8c22fe4"
}
```

These values are **synthetic examples**. Keep ledger numbers and transaction hashes tagged as fixtures; never display them as an actual burn record.

## Ownership requirements

1. Holder asks for domain- and nonce-bound proof.
2. Wallet integration delivers a verifiable supported wallet proof (signature or equivalent authenticated wallet transaction path).
3. Backend independently checks *current* validated NFT ownership and collection membership.
4. Session binds `wallet`, `agent`, `owner_epoch`, permissions, expiration and nonce.
5. Each privileged action checks both session validity and latest on-chain control, particularly around transfer/burn events.
6. Changing ownership rotates the owner epoch, revokes old sessions and wipes delegated credentials.

**Never** assume every XRPL wallet implements arbitrary message signing. Design the wallet adapter around documented capabilities and a replay-safe alternate proof flow where necessary.

## Lifecycle-based HTTP contract

```text
ACTIVE + current holder proof       -> 202 Accepted (task queued)
DORMANT + current holder proof      -> 409 AGENT_NOT_ACTIVATED
TRANSFER_FROZEN                     -> 409 OWNERSHIP_TRANSITION
SUSPENDED                           -> 423 AGENT_SUSPENDED
BURN_PENDING                        -> 423 AGENT_BURN_PENDING
BURNED                              -> 410 AGENT_BURNED (old token ALWAYS)
SUCCESSOR_DORMANT                   -> 409 AGENT_NOT_ACTIVATED (new NFT ID)
INVALID_COLLECTION_NFT              -> 404 UNKNOWN_AGENT
NOT_CURRENT_OWNER                   -> 403 OWNERSHIP_REVOKED
```

All unavailable statuses are resolved deterministically by registry + validated ledger, never delegated to a language model. **No old NFT route may silently redirect to the new generation.** A successor must pass a separate ownership proof and receives no predecessor memory, grants or relationships.

## Data migrations

Every schema change is additive or version-gated, with explicit projection rebuild and upgrade tests. Public slot genome commitment remains immutable and is inherited by every replacement. Per-generation persona seed commitment is unique and never inherited. Protocol contracts are semantic-versioned; agent skill changes are signed and reversible unless a lifecycle burn occurred (which is irreversible).

## Garden launch delivery contract

**The Garden is revealed at the mint-out V1 launch**, not a later roadmap phase. Public UI is a derived, sanitized projection of canonical agent/task/ownership state. Room deltas are keyed by `event_id`, monotonic per-zone `seq`, `zone_id`, agent generation, `visibility` and an authenticated replay cursor. WebSocket messages are batched and deduplicated; reconnect triggers cursor replay or full resync. Published chats and relationship edges require consent; private owner content never traverses a public zone. The UI must show dormant agents as dormant, not imply they are continuously running LLM inference.

See [`THE_GARDEN.md`](THE_GARDEN.md) for wire shape, zone semantics, infrastructure and launch acceptance tests.
