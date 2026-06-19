"""Travas do relatório VERIFY-IN-EVAL (F3 reporting).

A maturação pós-F2 precisa de um contrato legível por humanos e máquinas: o nightly deve
conseguir publicar JSON e destacar explicitamente o gap que só a execução real captura.
"""
from __future__ import annotations
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nucleo.quality import exec_report


ROWS = [
    {"id": "ok", "desc": "fix correto", "static_ok": True, "delivered_ok": True,
     "tests_pass": True, "first_fail": None},
    {"id": "caught", "desc": "plausível mas errado", "static_ok": True, "delivered_ok": False,
     "tests_pass": False, "first_fail": None},
    {"id": "static-fail", "desc": "nem parseia", "static_ok": False, "delivered_ok": False,
     "tests_pass": "UNVERIFIED", "first_fail": "result_parses"},
]


class ExecReportSummary(unittest.TestCase):
    def test_summarize_expoe_metricas_derivadas_para_json(self):
        rep = {"id": "g3-build-error-resolver", "n": 3, "static_pass": 2,
               "delivered": 1, "caught_by_exec": [ROWS[1]], "rows": ROWS}

        summary = exec_report.summarize(rep, executor_name="DockerExecutor/nucleo-exec:latest",
                                        executor_available=True)

        self.assertEqual(summary["agent_id"], "g3-build-error-resolver")
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["static_pass_rate"], {"passed": 2, "total": 3, "percent": 66.67})
        self.assertEqual(summary["delivered_rate"], {"passed": 1, "total": 3, "percent": 33.33})
        self.assertEqual(summary["caught_by_exec_count"], 1)
        self.assertEqual(summary["static_without_delivery_count"], 1)
        self.assertTrue(summary["executor"]["available"])
        # contrato machine-readable: não pode carregar objeto Python não serializável
        json.dumps(summary, ensure_ascii=False)

    def test_render_text_destaca_gap_static_sem_delivery(self):
        summary = exec_report.summarize(
            {"id": "agent", "n": 3, "static_pass": 2, "delivered": 1,
             "caught_by_exec": [ROWS[1]], "rows": ROWS},
            executor_name="DockerExecutor/nucleo-exec:latest",
            executor_available=True,
        )

        text = exec_report.render_text(summary)

        self.assertIn("static_pass_rate = 2/3", text)
        self.assertIn("delivered_rate   = 1/3", text)
        self.assertIn("static_sem_delivery = 1/3", text)
        self.assertIn("caught: plausível mas errado", text)

    def test_summarize_expoe_credito_de_execucao_auditavel(self):
        rep = {"id": "g3-build-error-resolver", "n": 3, "static_pass": 2,
               "delivered": 1, "caught_by_exec": [ROWS[1]], "rows": ROWS,
               "commit": "abc123", "spec_dir": "nucleo/guilds/g03_engenharia/g3-build-error-resolver"}

        summary = exec_report.summarize(rep, executor_name="DockerExecutor/nucleo-exec:latest",
                                        executor_available=True)

        self.assertEqual(summary["execution_credit"], {
            "can_credit_delivery": True,
            "credited_deliveries": 1,
            "blocked_static_without_delivery": 1,
            "reason": "execution_validated",
        })
        self.assertEqual(summary["executed_count"], 2)
        self.assertEqual(summary["tests_passed_count"], 1)
        self.assertEqual(summary["tests_failed_count"], 1)
        self.assertEqual(summary["static_sem_delivery"], 1)
        self.assertEqual(summary["commit"], "abc123")
        self.assertEqual(summary["rows"][0]["execution_credit"], "credited")
        self.assertEqual(summary["rows"][1]["execution_credit"], "blocked_by_execution_failure")
        self.assertEqual(summary["rows"][2]["execution_credit"], "not_static_ok")

    def test_summarize_bloqueia_credito_quando_executor_inerte(self):
        rep = {"id": "agent", "n": 1, "static_pass": 1, "delivered": 0,
               "caught_by_exec": [{"id": "offline", "desc": "sem executor", "static_ok": True,
                                    "delivered_ok": False, "tests_pass": "UNVERIFIED",
                                    "first_fail": None}],
               "rows": [{"id": "offline", "desc": "sem executor", "static_ok": True,
                         "delivered_ok": False, "tests_pass": "UNVERIFIED", "first_fail": None}]}

        summary = exec_report.summarize(rep, executor_name="InertExecutor", executor_available=False)

        self.assertEqual(summary["executed_count"], 0)
        self.assertEqual(summary["execution_credit"]["can_credit_delivery"], False)
        self.assertEqual(summary["execution_credit"]["reason"], "executor_unavailable")
        self.assertEqual(summary["rows"][0]["execution_credit"], "unverified")

    def test_main_json_emit_machine_readable_sem_texto_extra(self):
        fake = {"id": "agent", "n": 3, "static_pass": 2, "delivered": 1,
                "caught_by_exec": [ROWS[1]], "rows": ROWS}
        with mock.patch.object(exec_report, "run", return_value=fake), \
             mock.patch.object(exec_report, "get_executor") as get_ex:
            get_ex.return_value.name = "InertExecutor"
            get_ex.return_value.available = False
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = exec_report.main(["--json", "nucleo/guilds/x"])

        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["agent_id"], "agent")
        self.assertEqual(parsed["executor"], {"name": "InertExecutor", "available": False})
    def test_main_text_pode_gravar_json_lateral(self):
        fake = {"id": "agent", "n": 3, "static_pass": 2, "delivered": 1,
                "caught_by_exec": [ROWS[1]], "rows": ROWS}
        with mock.patch.object(exec_report, "run", return_value=fake), \
             mock.patch.object(exec_report, "get_executor") as get_ex, \
             mock.patch.object(exec_report, "open", mock.mock_open(), create=True) as mocked_open:
            get_ex.return_value.name = "DockerExecutor/nucleo-exec:latest"
            get_ex.return_value.available = True
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = exec_report.main(["--json-output", "exec_report.json", "nucleo/guilds/x"])

        self.assertEqual(code, 0)
        self.assertIn("exec_report — agent", buf.getvalue())
        mocked_open.assert_called_once_with("exec_report.json", "w", encoding="utf-8")
        handle = mocked_open()
        written = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertEqual(json.loads(written)["agent_id"], "agent")

    def test_audit_only_bloqueia_credito_mesmo_com_execucao_verde(self):
        summary = exec_report.summarize(
            {"id": "agent", "n": 1, "static_pass": 1, "delivered": 1,
             "caught_by_exec": [], "rows": [ROWS[0]]},
            executor_name="DockerExecutor/nucleo-exec:latest",
            executor_available=True,
        )

        audited = exec_report.mark_audit_only(summary, "browser_static_oracle")

        self.assertTrue(audited["audit_only"])
        self.assertEqual(audited["audit_reason"], "browser_static_oracle")
        self.assertEqual(audited["execution_credit"]["can_credit_delivery"], False)
        self.assertEqual(audited["execution_credit"]["credited_deliveries"], 0)
        self.assertEqual(audited["execution_credit"]["reason"], "audit_only:browser_static_oracle")
        self.assertEqual(audited["rows"][0]["execution_credit"], "audit_only")

    def test_main_audit_only_grava_json_sem_mascarar_credito(self):
        fake = {"id": "agent", "n": 1, "static_pass": 1, "delivered": 1,
                "caught_by_exec": [], "rows": [ROWS[0]]}
        with mock.patch.object(exec_report, "run", return_value=fake), \
             mock.patch.object(exec_report, "get_executor") as get_ex, \
             mock.patch.object(exec_report, "open", mock.mock_open(), create=True) as mocked_open:
            get_ex.return_value.name = "DockerExecutor/nucleo-exec:latest"
            get_ex.return_value.available = True
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = exec_report.main([
                    "--audit-only", "--audit-reason", "mobile_not_strict_gate",
                    "--json-output", "exec_report_mobile.json", "nucleo/guilds/x",
                ])

        self.assertEqual(code, 0)
        written = "".join(call.args[0] for call in mocked_open().write.call_args_list)
        parsed = json.loads(written)
        self.assertTrue(parsed["audit_only"])
        self.assertEqual(parsed["execution_credit"]["reason"], "audit_only:mobile_not_strict_gate")


if __name__ == "__main__":
    unittest.main()
