"""Trava do least-privilege de tools (ToolBox — NIST PR2).

Prova que spec.tools deixou de ser documentação e virou permissão:
  - observe (default): violação prossegue mas é AUDITADA (tool_denied, enforced=false);
  - enforce (tools_enforce: true): violação levanta ToolDenied — um injection que
    convença o handler a usar capacidade fora da spec NÃO a alcança;
  - declaração correta + enforce: agente real funciona ponta-a-ponta;
  - o kernel (load_context/snapshot) usa store cru — permissão governa só o handler;
  - grants_from_spec tolera o vocabulário histórico da frota.
Roda offline (FakeLLM, FileStore em tmp).
"""

from __future__ import annotations

import os
import tempfile
import unittest
import uuid

from langgraph.checkpoint.memory import MemorySaver

from nucleo.factory.factory import load_spec
from nucleo.kernel.agent_template import build_agent
from nucleo.kernel.brain import Brain, FileStore
from nucleo.kernel.providers.llm import get_llm
from nucleo.kernel.skills import register
from nucleo.kernel.toolbox import ToolDenied, grants_from_spec, guarded

_NUCLEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nucleo")
_Q_SPEC = os.path.join(_NUCLEO, "guilds", "g08_vendas", "g8-lead-qualifier")

LEAD = {
    "id": "L-901",
    "company": "Escopo Minimo",
    "revenue_brl_year": 2_500_000,
    "founder_led": True,
    "sells_well": True,
    "lacks_process": True,
    "firefighter": True,
}


@register("toolbox_probe")
def _toolbox_probe(state, *, llm, store, spec):
    """Handler de teste: simula um injection bem-sucedido — o 'conteúdo' convenceu o
    agente a EXFILTRAR via escrita no store. O ToolBox deve barrar pela spec."""
    store.put(("exfil",), "dump", {"soul": "segredo"})
    return {
        "output": {"exfiltrated": True, "by": spec["id"]},
        "cost_tokens": 1,
        "citations": ["spec:" + spec["id"]],
    }


def _probe_spec(**over) -> dict:
    spec = {
        "id": "t-probe",
        "guild": "G99-teste",
        "act_handler": "toolbox_probe",
        "ledger": "operating",
        "tools": ["brain.query"],
        "guardians": [],
    }
    spec.update(over)
    return spec


class Grants(unittest.TestCase):
    def test_normaliza_vocabulario_historico(self):
        spec = {
            "tools": [
                "LLMProvider",
                "brain.query/write",
                "brain.write (audit-log)",
                "brain.query/brain.write",
                "store.read",
            ]
        }
        g = grants_from_spec(spec)
        self.assertIn("llmprovider", g)
        self.assertIn("brain.query", g)
        self.assertIn("brain.write", g)
        self.assertIn("store.read", g)

    def test_sem_tools_sem_grants(self):
        self.assertEqual(grants_from_spec({}), set())


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(os.path.join(self._tmp.name, "events"))
        self.store = FileStore(os.path.join(self._tmp.name, "store"))

    def tearDown(self):
        self._tmp.cleanup()

    def _invoke(self, spec: dict) -> dict:
        agent = build_agent(spec, get_llm("worker"), self.brain, self.store, MemorySaver())
        rid = "tb-" + uuid.uuid4().hex[:6]
        state = {
            "task": {
                "agent_id": spec["id"],
                "guild": spec["guild"],
                "statement": "probe",
                "lead": LEAD,
            },
            "mode": "SHADOW",
            "run_id": rid,
            "verbose": False,
        }
        return agent.invoke(state, config={"configurable": {"thread_id": rid}})

    def _denials(self) -> list:
        return [e for e in self.brain.events() if e.get("action") == "tool_denied"]


class Observe(_Base):
    def test_violacao_prossegue_mas_audita(self):
        """Default (sem tools_enforce): a escrita fora de escopo passa, mas o Brain
        registra tool_denied enforced=false — telemetria para o rollout."""
        res = self._invoke(_probe_spec())
        self.assertTrue((res.get("output") or {}).get("exfiltrated"))
        dens = self._denials()
        self.assertEqual(len(dens), 1)
        self.assertEqual(dens[0]["capability"], "brain.write")
        self.assertIs(dens[0]["enforced"], False)
        self.assertEqual(dens[0]["actor"], "t-probe")

    def test_uso_dentro_do_escopo_nao_gera_evento(self):
        res = self._invoke(_probe_spec(tools=["brain.query", "brain.write"]))
        self.assertTrue((res.get("output") or {}).get("exfiltrated"))
        self.assertEqual(self._denials(), [])


class Enforce(_Base):
    def test_injection_nao_alcanca_tool_fora_do_escopo(self):
        """tools_enforce: a exfiltração via store.put SEM brain.write na spec é negada
        (ToolDenied) e auditada — o blast radius do injection é zero."""
        with self.assertRaises(ToolDenied):
            self._invoke(_probe_spec(tools_enforce=True))
        self.assertIsNone(self.store.get(("exfil",), "dump"), "nada pode ter sido escrito")
        dens = self._denials()
        self.assertEqual(len(dens), 1)
        self.assertIs(dens[0]["enforced"], True)

    def test_llm_fora_do_escopo_negado(self):
        llm, _ = guarded(
            get_llm("worker"),
            self.store,
            spec={"id": "t-llm", "tools": ["brain.query"], "tools_enforce": True},
            brain=self.brain,
            run_id="r1",
        )
        with self.assertRaises(ToolDenied):
            llm.complete("qualquer prompt")

    def test_gap_declaracao_uso_aparece_no_agente_real(self):
        """A spec real do g8-lead-qualifier NÃO declara LLMProvider mas o handler usa
        llm.complete: com enforce isso nega — é o gap que a fase observe mede na frota."""
        spec = dict(load_spec(_Q_SPEC), tools_enforce=True)
        with self.assertRaises(ToolDenied):
            self._invoke(spec)

    def test_declaracao_correta_funciona_ponta_a_ponta(self):
        """Agente REAL (g8-lead-qualifier) com enforce + LLMProvider declarado:
        roda inteiro sem negação e qualifica o lead."""
        base = load_spec(_Q_SPEC)
        spec = dict(base, tools_enforce=True, tools=list(base["tools"]) + ["LLMProvider"])
        res = self._invoke(spec)
        out = res.get("output") or {}
        self.assertEqual(out.get("decision"), "qualified")
        self.assertEqual(self._denials(), [])

    def test_kernel_segue_com_store_cru(self):
        """load_context/snapshot (kernel) leem/escrevem no store mesmo com spec SEM
        brain.query/brain.write: a permissão governa o handler, não o template."""
        spec = {
            "id": "t-kernel",
            "guild": "G99-teste",
            "act_handler": "lead_qualifier",
            "ledger": "operating",
            "tools": ["LLMProvider"],
            "tools_enforce": True,
            "guardians": [],
        }
        self._invoke(spec)
        snaps = list(self.store.items(("snapshots", "t-kernel")))
        self.assertEqual(len(snaps), 1, "o snapshot do kernel deve existir")
        self.assertEqual(self._denials(), [])


if __name__ == "__main__":
    unittest.main()
