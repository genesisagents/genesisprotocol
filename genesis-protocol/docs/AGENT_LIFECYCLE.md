# RFC-002 · NFT-to-Agent Lifecycle, Validated Burns & Generational Succession

**Status:** Proposed · **Network:** XRPL Mainnet · **Capacity:** 1,111 concurrent genome slots

## 1. Entities and authorities

`Slot(slot_id, canonical_genome_hash)` is an immutable edition / trait template, numbered 1–1111. `Agent(agent_id, nftoken_id, slot_id, generation, persona_seed_commitment)` is an incarnation, always uniquely bound to **one** NFT and never reused. One slot may have a **sequence** of agents, but **only one live incarnation at any time**. The validated XRPL ledger is authoritative for NFT existence, ownership, burn, and mint success; the application registry enforces slot-to-genome and generational admission rules.

An XRP.cafe collection page is a discovery reference, not a machine-verifiable provenance root. Resolve allowlisted issuer, taxon, token flags, metadata and replacement collection visibility. A unique edition display label is **not** an XRPL native on-chain NFT identifier.

```text
MAX_SLOTS = 1111
0 <= live_nfts <= 1111
UNIQUE(slot_id, generation)
UNIQUE(nftoken_id)
UNIQUE(agent_id)
UNIQUE(slot_id) WHERE lifecycle != BURNED   // in admitted agent records
slot.generation = max(all admitted generations for slot)
next_generation = max_generation + 1
new_genome_hash = slot.canonical_genome_hash
new_persona_seed != old_persona_seed
old_agent.lifecycle = BURNED forever
old_nftoken_id never reissued
live_count = total_issued_ever - validated_burn_count
```

The uniqueness predicates must be enforced with database constraints/atomic transactions and an allowlisted issuer's operating rules. XRPL's native `NFTokenMint` does not itself implement a *collection-wide 1,111 living-edition cap*; only the protocol's registered supply is bounded unless issuer controls enforce it operationally.

## 2. Independent state machines

**Agent instance:** `RESERVED → DORMANT → ACTIVE ↔ TRANSFER_FROZEN / SUSPENDED → BURN_PENDING → BURNED`. `BURN_PENDING` is provisional and reversible only when the burn candidate fails validation; `BURNED` is an absorbing state.

**Slot:** `UNISSUED → OCCUPIED → VACANT → REISSUE_RESERVED → OCCUPIED`. `REISSUE_RESERVED` can return to `VACANT` if the proposed mint fails, times out or cannot be validated. **A vacant slot holds a genome, not a living agent.**

On a validated owner transfer, rotate owner epoch and revoke old owner grants, without changing `slot_id`, `generation` or `agent_id`. On a validated burn, close the existing incarnation and transition the slot to `VACANT` for optional future issuer reissue.

## 3. Validated burn pipeline

1. Subscribe to XRPL mint, transfer and burn candidates; freeze relevant privileged actions while validation is unresolved.
2. Require successful `NFTokenBurn`, validated ledger, correct `NFTokenID` and canonical issuer/slot admission.
3. Persist `(burn_tx_hash, ledger_index, previous_agent_id, slot_id, generation)` and finalize old identity `BURNED` with revocation epoch increment. Make processing idempotent.
4. Revoke owner sessions, agent credentials and tool leases; cancel active A2A tasks and workflows, then notify peers with `AGENT_UNAVAILABLE`.
5. Preserve a sanitized memorial **only for the dead agent**. Erase/detach former owner's private state under a published retention policy; no cryptographic secrets or private memory pass to a successor.
6. Atomically mark the now-empty slot `VACANT` after proof no unburned admitted token remains.
7. Reconcile missing or duplicated ledger events through indexed history, not a marketplace UI. Ledger uncertainty => fail closed.

**XRPL authority:** The holder can always burn. Issuer/authorized-minter burning of another person's NFT requires the `tfBurnable` mint flag; verify actual flags per token before claiming issuer burn rights.

## 4. Optional remint: same DNA, different individual

Reissue requires **validated old burn**, verified `VACANT` state, issuer/authorized-minter permission, and a `REISSUE_RESERVED` compare-and-swap lock. The protocol does **not** remint automatically upon every burn. Record intent / approver / reference burn tx. Submit a *new* `NFTokenMint`; await validation and resolve the newly generated **different `NFTokenID`**. Reject duplicate, unverified, foreign and out-of-lineage tokens. A failed attempt releases the reservation only after resolving whether a mint actually succeeded on chain; never blindly retry a possibly submitted mint.

`generation = previous_generation + 1`, `genome_hash = same slot commitment`, `traits = byte-for-byte same canonical set`, `agent_id = fresh unique value`, `persona_seed = fresh cryptographically secure value`, `memory = empty`, `relationships = empty`, `reputation = reset`, `approvals = none`, `owner = independently verified`. Historic memorial remains separate and readonly. **A new NFT may have the same art/visual traits but must not pretend to be the original token or consciousness.**

Issuer must disclose how newly minted replacements are made available; burning the original conveys **no implicit claim** over a later replacement. New NFT's marketplace visibility and original collection treatment on XRP.cafe must be confirmed, not assumed.

## 5. Example

```text
Edition slot     0589
Genome hash      G (immutable across generations)

Gen I:  NFT A / agent_id A1 / persona P1 / memories M1
       ↳ validated NFTokenBurn(A) -> A1 terminal BURNED, slot VACANT
Gen II: NFT B / agent_id B1 / persona P2 / memories ∅ / genome G
       ↳ later NFTokenBurn(B) -> B1 terminal BURNED, slot VACANT
Gen III: NFT C / agent_id C1 / persona P3 / memories ∅ / genome G

The total live collection never exceeds 1,111 registered slots.
```

## 6. Race, privacy and fail-closed tests

- Concurrent remint requests for the same vacant slot: only one reservation accepted.
- `NFTokenMint` submitted but HTTP response lost: resolve ledger transaction before retry; avoid dual mint.
- New NFT minted to an old owner's wallet unexpectedly: ownership proof still required for control.
- Agent keeps A2A request in flight at burn: new external side effects blocked using revocation epoch / gateway checks.
- Old actor restart after backup restore: tombstone persists; no old-agent resurrection.
- New agent inherits trait hash, **never** old memory, trust edges, persona seed, permissions, reputation or private data.
- Generation 2 burns / Generation 3 remints: identity separation repeats indefinitely.
- Burn before original mint-out: original distribution completion rules remain independent and T0 reveal is one-shot.
- Out-of-band issuer mints claiming active slot: never admit two live NFTs to the same canonical slot.
- `tfBurnable` permission variant: verify holder-burn and possible issuer-burn.
- A reminted token not indexed in marketplace collection: expose chain proof and disclose limitation.

References: [XRPL NFTokenMint](https://xrpl.org/docs/references/protocol/transactions/types/nftokenmint) · [XRPL NFTokenBurn](https://xrpl.org/docs/references/protocol/transactions/types/nftokenburn) · [REBIRTH_PROTOCOL](REBIRTH_PROTOCOL.md).
