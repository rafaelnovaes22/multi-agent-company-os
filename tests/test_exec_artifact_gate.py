"""Gate dos artifacts JSON do foundry-exec (VERIFY-IN-EVAL F6).

A suíte de eval-cases é DISCRIMINANTE: tem casos positivos (devem entregar) e negativos
por design (plausível-mas-errado, adversariais, rejeitados no estático), que não entregam
de propósito. O gate por isso NÃO exige `credited == total` nem `tests_failed_count == 0`
(era a miscalibração que deixava o nightly em falso-RED). Ele garante: a execução rodou,
creditou entregas legítimas (>0), o oráculo classificou cada caso conforme o `expected`
(`oracle_correct`), e nenhum caso que o expected manda rejeitar foi creditado.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from nucleo.quality import exec_artifact_gate


def _row(rid, *, static_ok, expected_static_ok, credit, tests_pass=None):
    oc = (static_ok == expected_static_ok) if isinstance(expected_static_ok, bool) else None
    return {"id": rid, "static_ok": static_ok, "expected_static_ok": expected_static_ok,
            "execution_credit": credit, "tests_pass": tests_pass, "oracle_correct": oc}


def _healthy_rows():
    # 1 correto creditado + 1 plausível-mas-errado (passa estático, execução barra) +
    # 1 adversarial rejeitado no estático. Suíte discriminante SAUDÁVEL.
    return [
        _row("correto", static_ok=True, expected_static_ok=True, credit="credited", tests_pass=True),
        _row("plausivel-errado", static_ok=True, expected_static_ok=True,
             credit="blocked_by_execution_failure", tests_pass=False),
        _row("adversarial", static_ok=False, expected_static_ok=False,
             credit="not_static_ok", tests_pass="UNVERIFIED"),
    ]


def _summary(agent_id="agent", *, can_credit=True, credited=1, total=3,
             reason="execution_validated", rows=None):
    return {
        "agent_id": agent_id,
        "total": total,
        "executor": {"name": "DockerExecutor/nucleo-exec:latest", "available": True},
        "execution_credit": {
            "can_credit_delivery": can_credit,
            "credited_deliveries": credited,
            "blocked_static_without_delivery": 0,
            "reason": reason,
        },
        "rows": rows if rows is not None else _healthy_rows(),
    }


def _write(td, name, data):
    p = Path(td) / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


class ExecArtifactGateTest(unittest.TestCase):
    def test_passa_com_suite_discriminante_saudavel(self):
        # casos negativos (plausível-errado, adversarial) NÃO são regressão.
        with tempfile.TemporaryDirectory() as td:
            p1 = _write(td, "exec_report.json", _summary("g3-build-error-resolver"))
            p2 = _write(td, "exec_report_backend.json", _summary("g3-backend-builder"))
            result = exec_artifact_gate.evaluate_paths([p1, p2])
        self.assertTrue(result.ok, result.render())
        self.assertEqual(result.checked, 2)
        self.assertEqual(result.failures, [])
        self.assertIn("2 artifact(s) OK", result.render())

    def test_falha_quando_executor_indisponivel(self):
        bad = _summary(can_credit=False, credited=0, reason="executor_unavailable")
        bad["executor"] = {"name": "InertExecutor", "available": False}
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        self.assertIn("executor_unavailable", result.render())

    def test_falha_quando_sem_credito_real(self):
        # execução disponível mas nada creditado = caminho de execução não credita entrega.
        bad = _summary(can_credit=False, credited=0, reason="no_delivery_credited")
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        rendered = result.render()
        self.assertIn("credited_deliveries=0", rendered)
        self.assertIn("can_credit_delivery=false", rendered)

    def test_falha_quando_oracle_classifica_errado(self):
        # regressão REAL: um caso que deveria passar o estático não passou (static_ok != expected).
        rows = _healthy_rows()
        rows.append(_row("regrediu", static_ok=False, expected_static_ok=True,
                         credit="not_static_ok", tests_pass="UNVERIFIED"))
        bad = _summary(total=4, rows=rows)
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        self.assertIn("row regrediu: oracle_incorrect", result.render())

    def test_falha_quando_caso_a_rejeitar_e_creditado(self):
        # falso-positivo grave: expected manda rejeitar no estático, mas foi creditado.
        rows = _healthy_rows()
        rows.append(_row("falso-positivo", static_ok=True, expected_static_ok=False,
                         credit="credited", tests_pass=True))
        bad = _summary(total=4, credited=2, rows=rows)
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        rendered = result.render()
        self.assertIn("row falso-positivo: oracle_incorrect", rendered)  # static_ok=True != expected False
        self.assertIn("row falso-positivo: credited_but_should_reject", rendered)

    def test_falha_quando_negativo_por_design_entrega(self):
        # fail-safe violado (D3): caso com expected.exec_delivered=False que ENTREGOU —
        # plausível-mas-errado passando o held-out é resposta errada silenciosa.
        rows = _healthy_rows()
        row = _row("neg-entregou", static_ok=True, expected_static_ok=True,
                   credit="credited", tests_pass=True)
        row.update({"expected_exec_delivered": False, "delivered_ok": True})
        rows.append(row)
        bad = _summary(total=4, credited=2, rows=rows)
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        self.assertIn("row neg-entregou: delivered_but_designed_negative", result.render())

    def test_falha_quando_linhas_inconsistentes_com_total(self):
        bad = _summary(total=5)  # 3 rows, total=5
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        self.assertIn("rows_count=3/5", result.render())

    def test_falha_quando_total_zero(self):
        bad = _summary(total=0, credited=0, rows=[])
        with tempfile.TemporaryDirectory() as td:
            result = exec_artifact_gate.evaluate_paths([_write(td, "exec_report.json", bad)])
        self.assertFalse(result.ok)
        self.assertIn("total=0", result.render())

    def test_main_retorna_exit_code_1_em_falha(self):
        bad = _summary(can_credit=False, credited=0, reason="no_delivery_credited")
        with tempfile.TemporaryDirectory() as td:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = exec_artifact_gate.main([_write(td, "exec_report.json", bad)])
        self.assertEqual(code, 1)
        self.assertIn("VERIFY-IN-EVAL artifact gate FAILED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
