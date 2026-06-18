"""Gate dos artifacts JSON do forge-exec (VERIFY-IN-EVAL F6).

O nightly não deve apenas publicar relatórios: quando a execução real não credita
entrega, o workflow precisa falhar com um resumo acionável.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from nucleo.quality import exec_artifact_gate


def _summary(agent_id="agent", *, can_credit=True, credited=2, total=2, reason="execution_validated", rows=None):
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
        "executed_count": credited,
        "tests_failed_count": 0,
        "rows": rows if rows is not None else [
            {"id": "ok-1", "execution_credit": "credited", "tests_pass": True},
            {"id": "ok-2", "execution_credit": "credited", "tests_pass": True},
        ],
    }


class ExecArtifactGateTest(unittest.TestCase):
    def test_passa_quando_todos_artifacts_creditam_entrega_real(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "exec_report.json"
            p2 = Path(td) / "exec_report_backend.json"
            p1.write_text(json.dumps(_summary("g3-build-error-resolver")), encoding="utf-8")
            p2.write_text(json.dumps(_summary("g3-backend-builder", credited=1, total=1, rows=[
                {"id": "ok", "execution_credit": "credited", "tests_pass": True}
            ])), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(p1), str(p2)])

        self.assertTrue(result.ok)
        self.assertEqual(result.checked, 2)
        self.assertEqual(result.failures, [])
        self.assertIn("2 artifact(s) OK", result.render())

    def test_falha_quando_executor_indisponivel_ou_zero_credito(self):
        bad = _summary(can_credit=False, credited=0, reason="executor_unavailable", rows=[
            {"id": "offline", "execution_credit": "unverified", "tests_pass": "UNVERIFIED"}
        ])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(bad), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        self.assertEqual(result.checked, 1)
        rendered = result.render()
        self.assertIn("executor_unavailable", rendered)
        self.assertIn("credited_deliveries=0", rendered)
        self.assertIn("can_credit_delivery=false", rendered)

    def test_falha_quando_ha_linha_nao_creditada_ou_teste_falhando(self):
        rows = [
            {"id": "ok", "execution_credit": "credited", "tests_pass": True},
            {"id": "fail", "execution_credit": "blocked_by_execution_failure", "tests_pass": False},
            {"id": "maybe", "execution_credit": "unverified", "tests_pass": "UNVERIFIED"},
        ]
        bad = _summary(can_credit=True, credited=1, total=3, rows=rows)
        bad["tests_failed_count"] = 1
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(bad), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        rendered = result.render()
        self.assertIn("tests_failed_count=1", rendered)
        self.assertIn("row fail: blocked_by_execution_failure", rendered)
        self.assertIn("row maybe: unverified", rendered)

    def test_falha_quando_resumo_e_linhas_sao_inconsistentes(self):
        partial = _summary(credited=1, total=3, rows=[
            {"id": "ok", "execution_credit": "credited", "tests_pass": True},
        ])
        partial["executed_count"] = 1
        partial["tests_passed_count"] = 1
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(partial), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        rendered = result.render()
        self.assertIn("executed_count=1/3", rendered)
        self.assertIn("credited_deliveries=1/3", rendered)
        self.assertIn("rows_count=1/3", rendered)

    def test_falha_quando_executor_marca_indisponivel_mesmo_com_credito_inconsistente(self):
        inconsistent = _summary(can_credit=True, credited=1, total=1, rows=[
            {"id": "ok", "execution_credit": "credited", "tests_pass": True},
        ])
        inconsistent["executor"] = {"name": "InertExecutor", "available": False}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(inconsistent), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        self.assertIn("executor_unavailable", result.render())

    def test_falha_quando_total_zero_mesmo_com_credito_inconsistente(self):
        zero = _summary(can_credit=True, credited=1, total=0, rows=[])
        zero["executed_count"] = 0
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(zero), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        self.assertIn("total=0", result.render())

    def test_falha_quando_contadores_sobrecontam_total(self):
        over = _summary(can_credit=True, credited=2, total=1, rows=[
            {"id": "ok", "execution_credit": "credited", "tests_pass": True},
        ])
        over["executed_count"] = 2
        over["tests_passed_count"] = 2
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(over), encoding="utf-8")

            result = exec_artifact_gate.evaluate_paths([str(path)])

        self.assertFalse(result.ok)
        rendered = result.render()
        self.assertIn("credited_deliveries=2/1", rendered)
        self.assertIn("executed_count=2/1", rendered)

    def test_main_retorna_exit_code_1_em_falha(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "exec_report.json"
            path.write_text(json.dumps(_summary(can_credit=False, credited=0, reason="no_delivery_credited")), encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = exec_artifact_gate.main([str(path)])

        self.assertEqual(code, 1)
        self.assertIn("VERIFY-IN-EVAL artifact gate FAILED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
