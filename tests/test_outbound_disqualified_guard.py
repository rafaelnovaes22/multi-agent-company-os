"""Trava da decisão §6.7 (auditoria 2026-07-03): lead DISQUALIFIED não recebe outreach.

O bug latente: `outbound_sdr` ignorava `qualification.decision` e montava a sequência p/
qualquer lead — e os eval-cases disqualified CERTIFICAVAM isso (exigiam min_steps=3).
Agora: disqualified ⇒ bloqueio explícito (sequence vazia, blocked=True, human review),
nunca outreach silencioso; qualified segue com sequência completa + consent + sinais.
"""
import unittest

from nucleo.kernel.skills import _HANDLERS
from nucleo.kernel.providers.llm import FakeLLMProvider


def _run(decision, signals=None):
    handler = _HANDLERS["outbound_sdr"]
    state = {"task": {"lead": {"id": "L-1", "company": "Acme"},
                      "qualification": {"decision": decision,
                                        "icp_fit_signals": signals or {"sem_processo": True}}}}
    return handler(state, llm=FakeLLMProvider(), store=None,
                   spec={"id": "g8-outbound-sdr"})["output"]


class OutboundDisqualifiedGuardTest(unittest.TestCase):
    def test_disqualified_bloqueia_sem_sequencia(self):
        out = _run("disqualified")
        self.assertTrue(out["blocked"])
        self.assertEqual(out["sequence"], [])
        self.assertTrue(out["requires_human_review"])
        self.assertIn("disqualified", out["reason"])

    def test_qualified_segue_com_sequencia_completa(self):
        out = _run("qualified")
        self.assertGreaterEqual(len(out["sequence"]), 3)
        self.assertTrue(out["consent_required"])
        self.assertTrue(out["personalization_signals"])
        self.assertNotIn("blocked", out)


if __name__ == "__main__":
    unittest.main()
