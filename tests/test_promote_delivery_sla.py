"""Guarda do G7 — SLA de ENTREGA na promoção (decisão CEO 2026-06-30).

Trava que um agente só sobe a ASSISTED/AUTONOMOUS com `delivered_rate` do ORÁCULO EXECUTÁVEL
>= 95% — e que o gate é FAIL-CLOSED quando não há executor real (sem prova de entrega não
promove). É o que separa o número gameável (G4 estático ~100%) do número honesto (G7, execução).
O seam `_delivered_summary` é monkeypatched para não rodar Docker no teste.
"""
import unittest
from unittest import mock

from nucleo.governance import promote


def _summary(passed, total, *, available=True, name="docker"):
    return {
        "executor": {"name": name, "available": available},
        "delivered_rate": {"passed": passed, "total": total,
                           "percent": round(100 * passed / total, 2) if total else 0.0},
    }


class G7DeliverySlaTest(unittest.TestCase):
    def _gate(self, summary):
        with mock.patch.object(promote, "_delivered_summary", return_value=summary):
            return promote._gate("G7", {"id": "x"}, "spec/dir/x", {}, {})

    def test_acima_de_95_passa(self):
        ok, ev = self._gate(_summary(96, 100))
        self.assertTrue(ok)
        self.assertIn("96%", ev)

    def test_exatamente_95_passa(self):
        ok, _ = self._gate(_summary(95, 100))
        self.assertTrue(ok)   # limiar inclusivo

    def test_abaixo_de_95_reprova(self):
        ok, ev = self._gate(_summary(94, 100))
        self.assertFalse(ok)
        self.assertIn("thr=95%", ev)

    def test_caso_real_27pct_reprova(self):
        ok, _ = self._gate(_summary(8, 30))   # o número honesto de hoje
        self.assertFalse(ok)

    def test_executor_indisponivel_fail_closed(self):
        ok, ev = self._gate(_summary(0, 30, available=False, name="inert"))
        self.assertFalse(ok)
        self.assertIn("indisponível", ev)
        self.assertIn("fail-closed", ev)


class G7WiringTest(unittest.TestCase):
    def test_g7_exigido_para_assisted_e_autonomous(self):
        self.assertIn("G7", promote.REQUIRED[("PILOT", "ASSISTED")])
        self.assertIn("G7", promote.REQUIRED[("ASSISTED", "AUTONOMOUS")])

    def test_g7_nao_exigido_para_pilot(self):
        # SHADOW->PILOT ainda PROVA a entrega; o SLA cobra na entrada de ASSISTED.
        self.assertNotIn("G7", promote.REQUIRED[("SHADOW", "PILOT")])

    def test_threshold_e_95(self):
        self.assertEqual(promote.DELIVERED_THRESHOLD, 0.95)


if __name__ == "__main__":
    unittest.main()
