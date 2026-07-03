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

    def test_calculo_catalog_only_passa_sem_exigir_independent(self):
        # A exigência de >=1 independent fabricou os 380 do #66-80 (mesmo mecanismo do
        # guardrail 'não exigir human'): catalog-only é o estado HONESTO de cálculo/decisão
        # até existir fonte externa real — não reprova.
        cases = [{"id": "c1", "provenance": "catalog", "expected": {"cost_ratio": 0.2}},
                 {"id": "c2", "provenance": "catalog", "expected": {"cost_ratio": 0.3}}]
        sp = _mk_agent(self.tmp, "g8-calc-ok", "billing_calc", "G08-vendas-receita", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_independent_sem_lastro_reprova(self):
        # P1c: o carimbo do #66-80 — rótulo `independent` sem source externo nem held-out.
        cases = [{"id": "c1", "provenance": "independent", "expected": {"cost_ratio": 0.2}}]
        sp = _mk_agent(self.tmp, "g8-carimbo", "billing_calc", "G08-vendas-receita", cases)
        viol = pre_pr_gate._audit_agent(sp)
        self.assertTrue(any("SEM lastro" in v for v in viol))

    def test_independent_com_source_externo_passa(self):
        cases = [{"id": "c1", "provenance": "independent",
                  "source": "https://exemplo.gov/tabela-2026#v3",
                  "expected": {"cost_ratio": 0.2}}]
        sp = _mk_agent(self.tmp, "g8-fonte", "billing_calc", "G08-vendas-receita", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_independent_com_heldout_executavel_passa(self):
        cases = [{"id": "b1", "provenance": "independent",
                  "oracle": {"heldout_files": {"test_x.py": "assert True"}},
                  "expected": {"status": "pass"}}]
        sp = _mk_agent(self.tmp, "g3-exec-ok", "build_handler", "G03-engenharia", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_human_sem_ratified_by_reprova(self):
        cases = [{"id": "c1", "provenance": "human", "expected": {"cost_ratio": 0.2}}]
        sp = _mk_agent(self.tmp, "g8-human-forjado", "billing_calc", "G08-vendas-receita", cases)
        viol = pre_pr_gate._audit_agent(sp)
        self.assertTrue(any("ratified_by" in v for v in viol))

    def test_build_sem_heldout_reprova(self):
        # natureza build = handler spec_executor (executa artefato); sem held-out reprova.
        cases = [{"id": "b1", "provenance": "catalog", "expected": {"status": "pass"}}]
        sp = _mk_agent(self.tmp, "g3-build", "spec_executor", "G03-engenharia", cases)
        viol = pre_pr_gate._audit_agent(sp)
        self.assertTrue(any("held-out" in v for v in viol))

    def test_build_com_heldout_passa(self):
        cases = [{"id": "b1", "provenance": "catalog",
                  "oracle": {"heldout_files": {"test_x.py": "assert True"}},
                  "expected": {"status": "pass"}}]
        sp = _mk_agent(self.tmp, "g3-build-ok", "spec_executor", "G03-engenharia", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])

    def test_decisao_em_guilda_de_engenharia_nao_exige_heldout(self):
        # a heurística por guilda classificava errado os handlers de DECISÃO da G03:
        # exigir held-out de quem não produz artefato executável fabrica recompute
        # forjado. Natureza vem do handler; catalog-only é honesto p/ decisão.
        cases = [{"id": "d1", "provenance": "catalog", "expected": {"compatible": True}}]
        sp = _mk_agent(self.tmp, "g3-decisao", "api_contract_diff", "G03-engenharia", cases)
        self.assertEqual(pre_pr_gate._audit_agent(sp), [])


if __name__ == "__main__":
    unittest.main()
