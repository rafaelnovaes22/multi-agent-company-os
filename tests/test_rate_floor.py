"""Guarda do rate_floor — o piso de pass-rate do eval-harness.

Trava o contrato: estado igual-ou-melhor passa; qualquer regressão (por agente,
no TOTAL, agente novo sem piso) reprova; serialização é byte-estável para diff
revisável. É a prova de que a classe "0% executável mas verde-estrutural"
(lote G01–G03) volta a ser visível.
"""

import json
import os
import tempfile
import unittest

from nucleo.quality import rate_floor as rf


def _rep(aid, passed, total):
    return {"id": aid, "passed": passed, "total": total}


class CheckFloorTest(unittest.TestCase):
    def test_estado_igual_ao_piso_passa(self):
        reports = [_rep("a", 30, 30), _rep("b", 28, 30)]
        floor = rf.build_floor(reports)
        ok, violations = rf.check_floor(reports, floor)
        self.assertTrue(ok)
        self.assertEqual(violations, [])

    def test_melhora_acima_do_piso_passa(self):
        floor = rf.build_floor([_rep("a", 28, 30)])
        ok, _ = rf.check_floor([_rep("a", 30, 30)], floor)
        self.assertTrue(ok)

    def test_regressao_de_um_agente_reprova_com_o_id(self):
        floor = rf.build_floor([_rep("a-g1", 31, 31), _rep("b-g2", 30, 30)])
        ok, violations = rf.check_floor([_rep("a-g1", 0, 31), _rep("b-g2", 30, 30)], floor)
        self.assertFalse(ok)
        self.assertEqual(len(violations), 2)  # agente + TOTAL
        self.assertTrue(any("a-g1" in v for v in violations))
        self.assertTrue(any(v.startswith("TOTAL") for v in violations))
        self.assertFalse(any("b-g2" in v for v in violations))

    def test_colapso_total_reprova_mesmo_com_agentes_no_piso(self):
        # 15 agentes 100% -> 0%: o TOTAL cai junto (assinatura do lote G01-G03).
        before = [_rep(f"a{i:02d}", 31, 31) for i in range(15)]
        floor = rf.build_floor(before)
        after = [_rep(f"a{i:02d}", 0, 31) for i in range(15)]
        ok, violations = rf.check_floor(after, floor)
        self.assertFalse(ok)
        self.assertEqual(len([v for v in violations if v.startswith("TOTAL")]), 1)
        self.assertEqual(len(violations), 16)

    def test_agente_novo_sem_piso_reprova_ratchet(self):
        floor = rf.build_floor([_rep("a", 30, 30)])
        ok, violations = rf.check_floor([_rep("a", 30, 30), _rep("novo", 30, 30)], floor)
        self.assertFalse(ok)
        self.assertTrue(any("novo" in v and "sem piso" in v for v in violations))

    def test_agente_sem_casos_reprova(self):
        floor = rf.build_floor([_rep("a", 30, 30)])
        ok, violations = rf.check_floor([_rep("a", 0, 0)], floor)
        self.assertFalse(ok)
        self.assertTrue(any("sem casos" in v for v in violations))

    def test_piso_ausente_nao_e_dicio(self):
        self.assertIsNone(rf.load_floor(os.path.join(tempfile.gettempdir(), "piso-inexistente-xyz.json")))


class BuildWriteFloorTest(unittest.TestCase):
    def test_build_congela_taxas_e_total(self):
        floor = rf.build_floor([_rep("b", 28, 30), _rep("a", 30, 30)])
        self.assertEqual(floor["agents"]["a"], {"passed": 30, "total": 30, "rate": 1.0})
        self.assertAlmostEqual(floor["agents"]["b"]["rate"], 28 / 30)
        self.assertEqual(floor["total"], {"passed": 58, "total": 60, "rate": 58 / 60})
        self.assertEqual(list(floor["agents"]), ["a", "b"])  # ordenado: diff revisável

    def test_write_load_round_trip_byte_estavel(self):
        floor = rf.build_floor([_rep("a", 30, 30), _rep("b", 28, 30)])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "floor.json")
            rf.write_floor(p, floor)
            first = open(p, encoding="utf-8").read()
            rf.write_floor(p, rf.load_floor(p))
            second = open(p, encoding="utf-8").read()
        self.assertEqual(first, second)
        loaded = json.loads(first)
        self.assertEqual(loaded["agents"]["b"]["passed"], 28)


if __name__ == "__main__":
    unittest.main()
