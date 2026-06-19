"""Guarda do pre_pr_gate — o self-check HARD-FAIL que o loop do Hermes roda antes do PR.

Trava o comportamento que torna os pontos da avaliação do Hermes executáveis (regra de ouro
#4 do AGENTS.md): handler determinístico sem proveniência ou sem prova independente da
natureza REPROVA; handler genérico é fora de escopo; o exemplo correto passa. Ver o episódio
#30/#31/#32 (evals tautológicos que passaram em todos os gates verdes).
"""
import json
import os
import tempfile
import unittest

import yaml

from nucleo.quality import pre_pr_gate


def _mk_agent(root, aid, handler, guild, cases):
    d = os.path.join(root, aid)
    os.makedirs(os.path.join(d, "evals"))
    spec = {"id": aid, "guild": guild, "act_handler": handler}
    with open(os.path.join(d, "spec.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f)
    with open(os.path.join(d, "evals", "cases.json"), "w", encoding="utf-8") as f:
        json.dump(cases, f)
    return os.path.join(d, "spec.yaml")


class PrePrGateAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_handler_generico_fora_de_escopo(self):
        sp = _mk_agent(self.tmp, "g-router", "supervisor_route", "G09-customer-operations",
                       [{"id": "r1", "expected": {"routed_to": "x"}}])
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_calculo_sem_proveniencia_reprova(self):
        cases = [{"id": f"c{i}", "expected": {"cost_ratio": 0.2}} for i in range(3)]
        sp = _mk_agent(self.tmp, "g8-calc", "billing_calc", "G08-vendas-receita", cases)
        viol = pre_pr_gate._audit_agent(sp)
        self.assertTrue(any("sem `provenance`" in v for v in viol))
        self.assertTrue(any("human|independent" in v for v in viol))

    def test_calculo_com_proveniencia_independente_passa(self):
        cases = [{"id": "c1", "provenance": "human", "expected": {"cost_ratio": 0.2}},
                 {"id": "c2", "provenance": "catalog", "expected": {"cost_ratio": 0.3}}]
        sp = _mk_agent(self.tmp, "g8-calc-ok", "billing_calc", "G08-vendas-receita", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_build_sem_heldout_reprova(self):
        cases = [{"id": "b1", "provenance": "catalog", "expected": {"status": "pass"}}]
        sp = _mk_agent(self.tmp, "g3-build", "build_handler", "G03-engenharia", cases)
        viol = pre_pr_gate._audit_agent(sp)
        self.assertTrue(any("held-out" in v for v in viol))

    def test_build_com_heldout_passa(self):
        cases = [{"id": "b1", "provenance": "catalog",
                  "oracle": {"heldout_files": {"test_x.py": "assert True"}},
                  "expected": {"status": "pass"}}]
        sp = _mk_agent(self.tmp, "g3-build-ok", "build_handler", "G03-engenharia", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])


if __name__ == "__main__":
    unittest.main()
