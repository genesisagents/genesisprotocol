"""Dependency-free RFC invariant tests. These do not interact with XRPL Mainnet."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAP = 1111

class Lifecycle(str, Enum):
    DORMANT='DORMANT'
    ACTIVE='ACTIVE'
    BURN_PENDING='BURN_PENDING'
    BURNED='BURNED'

@dataclass(frozen=True)
class Agent:
    token: str
    agent_id: str
    generation: int
    genome: str
    persona_seed: str
    memory: tuple = ()
    relationships: tuple = ()
    reputation: int = 0

@dataclass
class Slot:
    genome: str
    current: Agent | None = None
    dead: list[Agent] = field(default_factory=list)

@dataclass
class Collection:
    slots: dict[int,Slot] = field(default_factory=dict)
    seen_tokens: set[str] = field(default_factory=set)
    seen_agent_ids: set[str] = field(default_factory=set)
    seen_personas: set[str] = field(default_factory=set)
    initial_mints: int = 0
    replacement_mints: int = 0
    validated_burn_count: int = 0
    mint_out_confirmed: bool = False

    @property
    def live(self):
        return sum(slot.current is not None for slot in self.slots.values())
    @property
    def cumulative(self):
        return self.initial_mints + self.replacement_mints
    def mint(self,slot_id,genome,token,agent_id,persona_seed,issuer_authorized=True):
        if not issuer_authorized: raise ValueError('ISSUER_UNAUTHORIZED')
        if not 1 <= slot_id <= CAP: raise ValueError('SLOT_OUT_OF_RANGE')
        if token in self.seen_tokens or agent_id in self.seen_agent_ids or persona_seed in self.seen_personas:
            raise ValueError('IDENTITY_REUSE')
        slot=self.slots.get(slot_id)
        if slot is None:
            if len(self.slots) == CAP: raise ValueError('CAP_REACHED')
            slot=Slot(genome)
            self.slots[slot_id]=slot
            generation=1
            self.initial_mints+=1
        else:
            if slot.current is not None: raise ValueError('SLOT_OCCUPIED')
            if not slot.dead: raise ValueError('UNVERIFIED_BURN')
            if slot.genome!=genome: raise ValueError('GENOME_MISMATCH')
            generation=slot.dead[-1].generation + 1
            self.replacement_mints+=1
        agent=Agent(token,agent_id,generation,genome,persona_seed)
        slot.current=agent
        self.seen_tokens.add(token);self.seen_agent_ids.add(agent_id);self.seen_personas.add(persona_seed)
        self.assert_invariants()
        return agent
    def burn(self,slot_id,validated=True):
        if not validated: raise ValueError('BURN_NOT_VALIDATED')
        slot=self.slots[slot_id]
        if slot.current is None: raise ValueError('NO_LIVE_AGENT')
        dead=slot.current;slot.dead.append(dead);slot.current=None
        self.validated_burn_count+=1
        self.assert_invariants()
        return dead
    def mark_mintout(self):
        self.mint_out_confirmed=True
    def assert_invariants(self):
        assert len(self.slots)<=CAP
        assert self.live<=CAP
        assert self.live==self.cumulative-self.validated_burn_count
        assert self.validated_burn_count==sum(len(s.dead) for s in self.slots.values())
        assert all(x.current is None or x.current.genome==x.genome for x in self.slots.values())
        assert all([x.generation for x in s.dead] == list(range(1,len(s.dead)+1)) for s in self.slots.values())

class Tests(unittest.TestCase):
    def test_all_schemas_parse(self):
        names=list((ROOT/'specs').glob('*.schema.json'))
        self.assertGreaterEqual(len(names),5)
        for n in names:
            d=json.loads(n.read_text())
            self.assertEqual(d['$schema'],'https://json-schema.org/draft/2020-12/schema')

    def test_integrated_garden_release_and_12_month_roadmap(self):
        readme=(ROOT/'README.md').read_text()
        roadmap=(ROOT/'docs/ROADMAP.md').read_text()
        garden=(ROOT/'docs/THE_GARDEN.md').read_text()
        self.assertIn('The Garden ships at the mint-out reveal',readme)
        self.assertIn('12-Month Post-Mint-Out',roadmap)
        self.assertIn('T0 · LAUNCH BASELINE',roadmap)
        self.assertIn('The Garden',roadmap.split('## QUARTER I')[0])
        for q,name in [(1,'SKILL EXTENSIBILITY'),(2,'COORDINATION ENGINE'),(3,'OPEN AGENT INTEROPERABILITY'),(4,'GENESIS NETWORK 2.0')]:
            self.assertIn(f'QUARTER {("I", "II", "III", "IV")[q-1]}',roadmap)
            self.assertIn(name,roadmap)
        self.assertNotIn('T+13',roadmap)
        self.assertNotIn('T+24',roadmap)
        self.assertIn('PixiJS',garden)
        self.assertIn('WebSocket',garden)
        self.assertIn('A2A',garden)
        self.assertIn('1,111',garden)
        self.assertIn('remint',garden.lower())

    def test_1111_simultaneous_slots_hardcap(self):
        c=Collection()
        for s in range(1,CAP+1):
            c.mint(s,f'genome-{s}',f'token-{s}',f'agent-{s}',f'persona-{s}')
        self.assertEqual(c.live,1111)
        with self.assertRaises(ValueError):c.mint(1112,'g','t','a','p')
        c.assert_invariants()

    def test_burn_then_same_traits_but_new_personality(self):
        c=Collection()
        first=c.mint(589,'g-589','token-old','agent-old','persona-old')
        assert c.burn(589) is first
        second=c.mint(589,'g-589','token-new','agent-new','persona-new')
        self.assertEqual(second.genome,first.genome)
        self.assertEqual(second.generation,2)
        self.assertNotEqual(second.token,first.token)
        self.assertNotEqual(second.agent_id,first.agent_id)
        self.assertNotEqual(second.persona_seed,first.persona_seed)
        self.assertEqual(second.memory,())
        self.assertEqual(second.relationships,())
        self.assertEqual(second.reputation,0)
        self.assertIn(first,c.slots[589].dead)

    def test_cumulative_supply_can_exceed_1111_but_live_cannot(self):
        c=Collection()
        for n in range(1,1112):c.mint(n,f'g{n}',f't{n}',f'a{n}',f'p{n}')
        c.mark_mintout()
        c.burn(589)
        self.assertEqual(c.live,1110)
        c.mint(589,'g589','t-rebirth-589','a-rebirth-589','p-rebirth-589')
        self.assertEqual((c.live,c.cumulative,c.validated_burn_count),(1111,1112,1))
        self.assertTrue(c.mint_out_confirmed)

    def test_cannot_remint_while_occupied(self):
        c=Collection();c.mint(1,'g','t','a','p')
        with self.assertRaisesRegex(ValueError,'SLOT_OCCUPIED'):c.mint(1,'g','t2','a2','p2')

    def test_replacement_traits_must_be_identical(self):
        c=Collection();c.mint(1,'original','t','a','p');c.burn(1)
        with self.assertRaisesRegex(ValueError,'GENOME_MISMATCH'):c.mint(1,'rerolled','t2','a2','p2')

    def test_burn_must_be_validated(self):
        c=Collection();c.mint(1,'g','t','a','p')
        with self.assertRaisesRegex(ValueError,'BURN_NOT_VALIDATED'):c.burn(1,validated=False)
        self.assertEqual(c.live,1)

    def test_no_predecessor_identity_or_persona_reuse(self):
        c=Collection();c.mint(1,'g','t','a','p');c.burn(1)
        for token,agent,persona in [('t','a2','p2'),('t2','a','p2'),('t2','a2','p')]:
            with self.assertRaisesRegex(ValueError,'IDENTITY_REUSE'):c.mint(1,'g',token,agent,persona)

    def test_three_generations_and_old_agents_stay_dead(self):
        c=Collection();first=c.mint(1,'g','t1','a1','p1');c.burn(1)
        second=c.mint(1,'g','t2','a2','p2');c.burn(1)
        third=c.mint(1,'g','t3','a3','p3')
        self.assertEqual(third.generation,3)
        self.assertEqual(c.slots[1].dead,[first,second])
        self.assertEqual(c.slots[1].current,third)

    def test_issuer_authorization_required(self):
        c=Collection();c.mint(1,'g','t1','a1','p1');c.burn(1)
        with self.assertRaisesRegex(ValueError,'ISSUER_UNAUTHORIZED'):
            c.mint(1,'g','t2','a2','p2',issuer_authorized=False)

    def test_mintout_monotonic_through_burn_and_remint(self):
        c=Collection();c.mint(1,'g','t1','a1','p1');c.mark_mintout()
        c.burn(1);c.mint(1,'g','t2','a2','p2')
        self.assertTrue(c.mint_out_confirmed)

if __name__=='__main__':unittest.main()
