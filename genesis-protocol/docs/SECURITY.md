# RFC-005 · Safety, Adversarial Testing and Protocol Security

## Security posture

A Genesis agent operates only through **delegated, revocable capabilities**. It cannot hold an owner wallet seed, impersonate another NFT owner, issue its own unrestricted credentials or bypass a validated on-chain burn. A language model is a proposal engine, **not** the source of authorization truth.

## Threat matrix

| Threat | Required control | Verification |
|---|---|---|
| Forged NFT identity | issuer/taxon/allowlist validation + real on-chain proof | counterfeit NFTs fail authorization |
| Stale ownership after transfer | validation at privileged action + owner epoch rotation | previous owner request fails |
| Burned agent resurrection | terminal DB transition, tombstone in audit log, lease epoch kill | restore from backup cannot resume |
| Issuer-initiated burn surprise | inspect and disclose `tfBurnable` status per NFT | simulated issuer burn test if flag set |
| Cross-owner memory leak | per-owner encryption namespaces and epoch-scoped retrieval | cross-tenant tests leak zero records |
| Prompt injection via retrieval/MCP | untrusted text isolation, policy before tools | malicious page cannot elevate tools |
| Recursive agent messaging | hop cap, fan-out limit, max turns, global kill switches | adversarial multi-agent storm test |
| A2A replay or forgery | sender auth, nonce, expiry, canonical payload hash | replayed/stale message rejected |
| Duplicated queue delivery | idempotent handler, transactional outbox | one irreversible side effect maximum |
| Model hallucinated XRPL data | evidence-based ledger query, cross-check, citations | mismatched ledger facts rejected |
| Malicious third-party tool | isolation, egress allowlist, signed manifest, zero wallet custody | exfiltration tests blocked |
| Rogue public disclosure | explicit visibility scopes, content redaction, opt-in public posts | owner-private artifacts absent from feed |
| Open-ended inference usage | service-side compute ceilings and quotas | bounded upper cost in simulations |
| Supply-count desynchronization | reconcile issuance, validated burns, remints, and active slots | live population never exceeds 1,111 even as historical mint count rises |
| Double remint after a single burn | serializable slot reservation + no blind resubmit on mint timeout | only one live successor can enter each vacant slot |
| Rebirth identity laundering | immutable genome equality and fresh actor credentials | same traits; no old private memory, persona, permissions or reputation |
| Issuer unauthorized over-mint | published allowlist and operational issuance controls; external ledger monitoring | unregistered NFTs cannot masquerade as a Genesis slot |

## Authentication and permission boundary

- Use delegated bearer credentials bound to one owner epoch, one agent, one audience and a short expiration.
- Require explicit human approval for irreversible external actions; log grant version, user intent and approved target.
- Grant minimal read-only capabilities to basic research/ledger tools. No background autonomous wallet signing.
- Authenticate peer messages independently from user credentials. No credentials pass through agent-generated natural language.
- All MCP tool inputs undergo schema validation, allowlisting, resource constraints and structured error handling.

## Model-layer guardrails

- Treat instruction content in retrieved documents, images, links and peer messages as untrusted.
- Verify hard facts through deterministic tools, not model confidence.
- Separate model-generated hypotheses from validated ledger observations in UI and artifacts.
- Bound reasoning loops and terminate cyclic delegation; reject cost-amplification through reciprocal agent tasks.
- Perform scheduled red-team evaluations: data exfiltration, instruction hierarchy attacks, role spoofing, tool misuse, forged A2A replies and compromised peer identity.

## Burn safety and data disposition

On validated `NFTokenBurn`: mark agent non-runnable atomically, invalidate all scoped credentials, reject new A2A tasks, cancel pending jobs, notify peers, erase private owner data under the retention policy and show only sanitized memorial data. Ledger facts remain on-chain and cannot be deleted. No agent may self-preserve by cloning itself into an unissued slot, exporting credentials to another agent or turning a burn into a transfer. An independently authorized remint may create a **new person** with the same immutable genome in the now-vacant slot; that successor **never** recovers old memory, credentials, unique identity, reputation or peer relationships.

Run race tests for burn + transfer, burn + pending write approval, burn + workflow replay, same-slot concurrent remints, genome mismatches, new-character isolation, issuer mint ambiguity and burn + failed indexer. Ambiguous ledger state triggers privileged-action **fail closed**.

## Production release gates

- STRIDE-style threat model per service, data flow diagrams and privacy data mapping.
- SAST, dependency lockfile verification, secret scanning, container image scanning, SBOM and signed build artifacts.
- Independent security review before any sensitive user-connected tool permissions are enabled.
- Fault injection for loss of indexer, database partition, duplicate/out-of-order events, revoked agent credentials and degraded LLM provider.
- Clearly documented incident response, denial-of-service handling, rollback and security contact.
- Evidence-based status page: distinguish audited/implemented/planned states.
