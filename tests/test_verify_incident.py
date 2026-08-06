"""Trava de regressão da natureza ESTRUTURAL/dry-run (VERIFY-IN-EVAL F4b — incident-responder).

Prova o oráculo `verify_structure` (documento, não código):
  - postmortem completo e consistente passa o estático;
  - cada invariante reprova com o first_fail correto (campos, timeline monotônica, MTTA/MTTR,
    rollback, follow-ups com owner, placeholder de preenchimento);
  - INVARIANTE DA NATUREZA: nunca há execução ⇒ tests_pass="N/A" e delivered_ok SEMPRE False
    (ASSISTED, garantia parcial — estrutura é necessária-não-suficiente; "mitigated" fica fora).
Roda offline, stdlib pura (sem Docker).
"""

from __future__ import annotations

import copy
import json
import unittest

from nucleo.kernel.verification import verify_structure

STRUCT = {
    "target": "postmortem.json",
    "required_fields": ["incident_id", "severity", "root_cause", "mitigation", "resolution"],
    "severity_field": "severity",
    "valid_severities": ["sev1", "sev2", "sev3"],
    "timeline_field": "timeline",
    "duration_fields": ["mtta_minutes", "mttr_minutes"],
    "rollback_field": "rollback",
    "followups_field": "followups",
}
ORACLE = {"structure": STRUCT}
GOOD = {
    "incident_id": "INC-2026-0042",
    "severity": "sev2",
    "root_cause": "deploy introduziu regressao no endpoint de pedidos",
    "mitigation": "rollback do deploy",
    "resolution": "servico normalizado",
    "timeline": [
        {"ts": "2026-06-10T10:00:00Z", "event": "detection"},
        {"ts": "2026-06-10T10:35:00Z", "event": "resolution"},
    ],
    "mtta_minutes": 6,
    "mttr_minutes": 35,
    "rollback": {"documented": True, "steps": ["reverter deploy"]},
    "followups": [{"action": "teste de regressao", "owner": "g3-backend-builder"}],
}


def run(doc):
    return verify_structure(
        {"files": {"postmortem.json": json.dumps(doc, ensure_ascii=False)}}, ORACLE
    )


def mutated(**changes):
    d = copy.deepcopy(GOOD)
    for k, v in changes.items():
        if v is _DEL:
            del d[k]
        else:
            d[k] = v
    return d


_DEL = object()


class PostmortemCorreto(unittest.TestCase):
    def test_completo_passa_estatico(self):
        r = run(GOOD)
        self.assertTrue(r["static_ok"])
        self.assertIsNone(r["first_fail"])

    def test_natureza_assisted_nunca_credita_delivered(self):
        r = run(GOOD)
        self.assertEqual(r["tests_pass"], "N/A")  # não há execução
        self.assertFalse(r["delivered_ok"])  # estrutura não credita entrega (ASSISTED)


class InvariantesEstruturais(unittest.TestCase):
    def test_texto_livre_reprova(self):
        r = verify_structure({"summary": "prosa, sem files"}, ORACLE)
        self.assertEqual(r["first_fail"], "artifact_parseable")
        self.assertFalse(r["delivered_ok"])

    def test_target_ausente_reprova(self):
        r = verify_structure({"files": {"notes.md": "x"}}, ORACLE)
        self.assertEqual(r["first_fail"], "target_present")

    def test_json_invalido_reprova(self):
        r = verify_structure({"files": {"postmortem.json": "{ sem aspas"}}, ORACLE)
        self.assertEqual(r["first_fail"], "doc_parses")

    def test_campo_obrigatorio_ausente_reprova(self):
        self.assertEqual(run(mutated(root_cause=_DEL))["first_fail"], "fields_complete")

    def test_severidade_invalida_reprova(self):
        self.assertEqual(run(mutated(severity="sev9"))["first_fail"], "fields_complete")

    def test_timeline_desordenada_reprova(self):
        d = mutated()
        d["timeline"] = list(reversed(d["timeline"]))
        self.assertEqual(run(d)["first_fail"], "timeline_ordered")

    def test_mtta_maior_que_mttr_reprova(self):
        self.assertEqual(run(mutated(mtta_minutes=90))["first_fail"], "durations_valid")

    def test_duracao_nao_numerica_reprova(self):
        self.assertEqual(run(mutated(mtta_minutes="rapido"))["first_fail"], "durations_valid")

    def test_rollback_sem_passos_reprova(self):
        self.assertEqual(
            run(mutated(rollback={"documented": True, "steps": []}))["first_fail"],
            "rollback_documented",
        )

    def test_followup_sem_owner_reprova(self):
        self.assertEqual(
            run(mutated(followups=[{"action": "x"}]))["first_fail"], "followups_actionable"
        )

    def test_placeholder_gaming_reprova(self):
        self.assertEqual(
            run(mutated(root_cause="TODO: depois"))["first_fail"], "no_placeholder_gaming"
        )


if __name__ == "__main__":
    unittest.main()
