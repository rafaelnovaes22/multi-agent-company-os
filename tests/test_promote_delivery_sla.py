"""Guarda do G7 — SLA de ENTREGA na promoção (decisão CEO 2026-06-30).

Trava que um agente só sobe a ASSISTED/AUTONOMOUS com `delivered_eligible_rate` do ORÁCULO
EXECUTÁVEL >= 95% — medido sobre os casos ELEGÍVEIS (expected.exec_delivered=True; a suíte é
discriminante e os negativos-por-design medem o fail-safe, não a entrega). Fail-closed sem
executor real E sem casos elegíveis; falso-positivo de entrega (negativo que entrega) é
HARD-FAIL independente da taxa. O seam `_delivered_summary` é monkeypatched para não rodar
Docker no teste.
"""

import unittest
from unittest import mock

from nucleo.governance import promote


def _summary(passed, total, *, raw=None, false_positives=0, available=True, name="docker"):
    def rate(p, t):
        return {"passed": p, "total": t, "percent": round(100 * p / t, 2) if t else 0.0}

    raw_passed, raw_total = raw or (passed, total)
    return {
        "executor": {"name": name, "available": available},
        "delivered_rate": rate(raw_passed, raw_total),
        "delivered_eligible_rate": rate(passed, total),
        "false_positive_delivery_count": false_positives,
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
        self.assertTrue(ok)  # limiar inclusivo

    def test_abaixo_de_95_reprova(self):
        ok, ev = self._gate(_summary(94, 100))
        self.assertFalse(ok)
        self.assertIn("thr=95%", ev)

    def test_caso_real_8_de_8_elegiveis_passa_com_bruto_8_de_30(self):
        # O nightly real: 8/30 bruto, mas TODOS os 8 casos elegíveis entregaram — a
        # suíte tem 22 negativos-por-design que medem o fail-safe, não a entrega.
        ok, ev = self._gate(_summary(8, 8, raw=(8, 30)))
        self.assertTrue(ok)
        self.assertIn("8/8", ev)
        self.assertIn("bruto 8/30", ev)

    def test_gap_de_capacidade_real_reprova(self):
        ok, _ = self._gate(_summary(6, 8, raw=(6, 30)))  # 75% nos elegíveis
        self.assertFalse(ok)

    def test_falso_positivo_e_hard_fail_mesmo_com_100pct(self):
        # Negativo-por-design que ENTREGA = resposta errada silenciosa: viola o
        # invariante dos <=5% (D3) e reprova independente da taxa nos elegíveis.
        ok, ev = self._gate(_summary(8, 8, raw=(9, 30), false_positives=1))
        self.assertFalse(ok)
        self.assertIn("falso-positivo", ev)
        self.assertIn("HARD-FAIL", ev)

    def test_suite_sem_casos_elegiveis_fail_closed(self):
        # Natureza sem oráculo executável de entrega (estrutural/browser) ou suíte
        # não-instrumentada: sem denominador não há SLA medível — não promove.
        ok, ev = self._gate(_summary(0, 0, raw=(0, 30)))
        self.assertFalse(ok)
        self.assertIn("0 casos elegíveis", ev)
        self.assertIn("fail-closed", ev)

    def test_executor_indisponivel_fail_closed(self):
        ok, ev = self._gate(_summary(0, 8, raw=(0, 30), available=False, name="inert"))
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
