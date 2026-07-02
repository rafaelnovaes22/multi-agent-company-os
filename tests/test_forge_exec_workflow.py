"""Travas estáticas do workflow forge-exec ampliado (VERIFY-IN-EVAL F7).

Os relatórios opcionais de naturezas novas devem ser publicados sem enfraquecer o
gate F6: artifacts ainda não creditáveis aparecem para auditoria, mas não entram no
gate estrito de crédito real até terem runtime seguro e verde.
"""
from __future__ import annotations

import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/forge-exec.yml")


class ForgeExecExpandedReportsTest(unittest.TestCase):
    def test_workflow_publica_browser_incident_como_auditoria_e_mobile_estrito(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("exec_report_browser.json", text)
        self.assertIn("exec_report_mobile.json", text)
        self.assertIn("exec_report_incident.json", text)
        self.assertIn("nucleo/guilds/g04_qualidade_eval/g4-e2e-playwright", text)
        self.assertIn("nucleo/guilds/g03_engenharia/g3-mobile-builder", text)
        self.assertIn("nucleo/guilds/g03_engenharia/g3-incident-responder", text)
        # browser + incident seguem auditoria (naturezas sem execução real creditável);
        # o mobile foi PROMOVIDO ao gate estrito em 2026-07-01 (harness consertado, 30/30).
        self.assertGreaterEqual(text.count("--audit-only"), 2)
        self.assertIn("browser_static_oracle", text)
        self.assertNotIn("mobile_not_in_strict_gate", text)
        self.assertIn("incident_structural_oracle", text)
        self.assertGreaterEqual(text.count("continue-on-error: true"), 2)

    def test_gate_f6_mantem_apenas_artifacts_creditaveis_por_execucao_real(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        gate_start = text.index("python -m nucleo.quality.exec_artifact_gate")
        upload_start = text.index("- name: Publicar artefatos")
        gate_block = text[gate_start:upload_start]

        self.assertIn("exec_report.json", gate_block)
        self.assertIn("exec_report_backend.json", gate_block)
        self.assertIn("exec_report_frontend.json", gate_block)
        self.assertIn("exec_report_infra.json", gate_block)
        self.assertIn("exec_report_mobile.json", gate_block)   # estrito desde 2026-07-01
        self.assertNotIn("exec_report_browser.json", gate_block)
        self.assertNotIn("exec_report_incident.json", gate_block)

    def test_optional_artifacts_sao_uploadados_para_auditoria(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        upload_start = text.index("- name: Publicar artefatos")
        upload_block = text[upload_start:]

        for name in [
            "exec_report_browser.txt",
            "exec_report_browser.json",
            "exec_report_mobile.txt",
            "exec_report_mobile.json",
            "exec_report_incident.txt",
            "exec_report_incident.json",
        ]:
            self.assertIn(name, upload_block)
        self.assertIn("if: always()", upload_block)


if __name__ == "__main__":
    unittest.main()
