"""Trava da resiliência operacional (NIST "sobreviver ao inevitável" — PR1).

Prova que o caminho de DESCIDA não tem fricção nem gate:
  - demote(): qualquer modo -> SHADOW sem pré-condições, auditado append-only;
  - kill-switch de frota (store ou env FLEET_KILL_SWITCH): o gate runtime de TODO
    agente passa a se comportar como SHADOW — sem entrega, sem cobrança, sem pausa
    de aprovação — mesmo em AUTONOMOUS/ASSISTED, sem tocar nos modos persistidos;
  - soltar o switch devolve a frota ao estado promovido (caminho feliz intacto).
Roda offline (FakeLLM, FileStore em tmp).
"""

from __future__ import annotations

import os
import tempfile
import unittest
import uuid

from langgraph.checkpoint.memory import MemorySaver

from nucleo.factory.factory import build_from_spec
from nucleo.governance.promote import current_mode, demote, set_fleet_kill_switch
from nucleo.kernel.brain import Brain, FileStore
from nucleo.kernel.gates import KILL_SWITCH_ENV, kill_switch_on
from nucleo.kernel.providers.llm import get_llm

_NUCLEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nucleo")
_Q_SPEC = os.path.join(_NUCLEO, "guilds", "g08_vendas", "g8-lead-qualifier")

LEAD = {
    "id": "L-900",
    "company": "Contencao Rapida",
    "revenue_brl_year": 2_500_000,
    "founder_led": True,
    "sells_well": True,
    "lacks_process": True,
    "firefighter": True,
}


def _task(mode: str) -> dict:
    return {
        "task": {
            "agent_id": "g8-lead-qualifier",
            "guild": "G08-vendas-receita",
            "statement": "Qualificar lead contra o ICP",
            "lead": LEAD,
        },
        "mode": mode,
        "ledger": "billable",
        "run_id": "ks-" + uuid.uuid4().hex[:6],
        "verbose": False,
    }


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(os.path.join(self._tmp.name, "events"))
        self.store = FileStore(os.path.join(self._tmp.name, "store"))
        self._env = os.environ.pop(KILL_SWITCH_ENV, None)

    def tearDown(self):
        if self._env is not None:
            os.environ[KILL_SWITCH_ENV] = self._env
        else:
            os.environ.pop(KILL_SWITCH_ENV, None)
        self._tmp.cleanup()

    def _agent(self):
        _, agent, _ = build_from_spec(
            _Q_SPEC, get_llm("worker"), self.brain, self.store, MemorySaver()
        )
        return agent

    def _invoke(self, mode: str) -> dict:
        rid = "t-" + uuid.uuid4().hex[:6]
        return self._agent().invoke(_task(mode), config={"configurable": {"thread_id": rid}})


class Demote(_Base):
    def test_demote_derruba_para_shadow_sem_gates(self):
        """PILOT -> SHADOW sem pré-condição nenhuma (nada de eval/SLA/aprovação)."""
        self.store.put(("modes", "g8-lead-qualifier"), "current", "PILOT")
        res = demote(_Q_SPEC, "anomalia no audit trail", {"actor": "dri"}, self.brain, self.store)
        self.assertTrue(res["ok"])
        self.assertEqual(res["from"], "PILOT")
        self.assertEqual(current_mode(self.store, "g8-lead-qualifier"), "SHADOW")

    def test_demote_e_auditada_append_only(self):
        """O evento sai no Brain e a transição entra no log de promoções com reason."""
        self.store.put(("modes", "g8-lead-qualifier"), "current", "AUTONOMOUS")
        demote(
            _Q_SPEC,
            "exploit em producao",
            {"actor": "security-privacy-guardian"},
            self.brain,
            self.store,
        )
        evs = [e for e in self.brain.events() if e.get("action") == "demotion"]
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["from"], "AUTONOMOUS")
        self.assertEqual(evs[0]["reason"], "exploit em producao")
        log = self.store.get(("promotions", "g8-lead-qualifier"), "log")
        self.assertEqual(log[-1]["action"], "demotion")
        self.assertEqual(log[-1]["to"], "SHADOW")

    def test_demote_idempotente_em_shadow(self):
        res = demote(_Q_SPEC, "drill", {}, self.brain, self.store)
        self.assertTrue(res["ok"])
        self.assertEqual(res["from"], "SHADOW")
        self.assertEqual(current_mode(self.store, "g8-lead-qualifier"), "SHADOW")


class KillSwitch(_Base):
    def test_off_autonomous_entrega_normal(self):
        """Caminho feliz intacto: sem switch, AUTONOMOUS entrega e o output flui."""
        out = self._invoke("AUTONOMOUS").get("output") or {}
        self.assertIs(out.get("delivered"), True)
        self.assertNotIn("fleet_kill_switch", out)

    def test_on_via_store_contem_autonomous(self):
        """Com o switch no store, nem AUTONOMOUS entrega/cobra (vira SHADOW)."""
        set_fleet_kill_switch(True, "incidente", {"actor": "dri"}, self.brain, self.store)
        out = self._invoke("AUTONOMOUS").get("output") or {}
        self.assertIs(out.get("delivered"), False)
        self.assertEqual(out.get("billing_amount"), 0)
        self.assertIs(out.get("fleet_kill_switch"), True)

    def test_on_assisted_nao_pausa_nem_entrega(self):
        """Frota contida não pede aprovação: ASSISTED não emite interrupt nem entrega."""
        set_fleet_kill_switch(True, "incidente", {"actor": "dri"}, self.brain, self.store)
        res = self._invoke("ASSISTED")
        self.assertNotIn("__interrupt__", res)
        out = res.get("output") or {}
        self.assertIs(out.get("delivered"), False)
        self.assertEqual(out.get("billing_amount"), 0)

    def test_on_via_env_sem_store(self):
        """Override de emergência por env funciona mesmo sem flag no store."""
        os.environ[KILL_SWITCH_ENV] = "1"
        self.assertTrue(kill_switch_on(store=None))
        out = self._invoke("AUTONOMOUS").get("output") or {}
        self.assertIs(out.get("delivered"), False)

    def test_release_devolve_estado_promovido(self):
        """Ligar e soltar o switch não toca os modos persistidos: a frota volta a entregar."""
        set_fleet_kill_switch(True, "drill", {"actor": "dri"}, self.brain, self.store)
        self.assertTrue(kill_switch_on(self.store))
        set_fleet_kill_switch(False, "drill encerrado", {"actor": "dri"}, self.brain, self.store)
        self.assertFalse(kill_switch_on(self.store))
        out = self._invoke("AUTONOMOUS").get("output") or {}
        self.assertIs(out.get("delivered"), True)
        evs = [e for e in self.brain.events() if e.get("action") == "fleet_kill_switch"]
        self.assertEqual([e["on"] for e in evs], [True, False])


if __name__ == "__main__":
    unittest.main()
