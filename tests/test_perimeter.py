"""Travas do G-PERÍMETRO — prova de entrega com credencial distinta do promotor.

O que está travado:
  1. o caminho feliz devolve o summary do agente + proof {run_id, commit, artifact};
  2. FAIL-CLOSED em cada elo: gh indisponível, sem run verde confiável, run velho,
     download falho, artifact sem o agente;
  3. só eventos confiáveis (schedule/workflow_dispatch) contam como perímetro;
  4. replay vs generativo são selecionados pelo flag do artifact, nunca misturados;
  5. no G7: req delivery_proof=ci-perimeter usa o perímetro (evidence nomeia o run) e
     reprova fail-closed quando não há prova — sem degradar p/ execução local.
"""
import datetime
import json
import os
import unittest
from unittest import mock

from nucleo.governance import perimeter, promote


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _runner(runs=None, files=None):
    """Runner fake do gh: `run list` devolve `runs`; `run download` materializa `files`."""
    def run(args, **_):
        if args[:2] == ["run", "list"]:
            return json.dumps(runs if runs is not None else [])
        if args[:2] == ["run", "download"]:
            if files is None:
                return None
            dest = args[args.index("-D") + 1]
            for name, data in files.items():
                with open(os.path.join(dest, name), "w", encoding="utf-8") as f:
                    json.dump(data, f)
            return ""
        return None
    return run


GREEN_RUN = {"databaseId": 123, "headSha": "abc123def456", "createdAt": _now_iso(),
             "event": "schedule", "workflowName": "foundry-exec (nightly)"}
REPLAY = {"agent_id": "g3-backend-builder", "generative": False,
          "delivered_eligible_rate": {"passed": 8, "total": 8, "percent": 100.0},
          "delivered_rate": {"passed": 8, "total": 30, "percent": 26.67},
          "false_positive_delivery_count": 0,
          "executor": {"name": "docker", "available": True}}
GEN = dict(REPLAY, generative=True)


class PerimeterFetchTest(unittest.TestCase):
    def test_caminho_feliz_devolve_summary_e_prova(self):
        got = perimeter.fetch_perimeter_summary(
            "g3-backend-builder",
            runner=_runner([GREEN_RUN], {"exec_report_backend.json": REPLAY,
                                         "exec_report_gen_backend.json": GEN}))
        self.assertIsNotNone(got)
        self.assertEqual(got["summary"]["delivered_eligible_rate"]["passed"], 8)
        self.assertFalse(got["summary"].get("generative"))
        self.assertEqual(got["proof"]["run_id"], "123")
        self.assertEqual(got["proof"]["commit"], "abc123def456")

    def test_generative_seleciona_o_relatorio_da_fase_geradora(self):
        got = perimeter.fetch_perimeter_summary(
            "g3-backend-builder", generative=True,
            runner=_runner([GREEN_RUN], {"exec_report_backend.json": REPLAY,
                                         "exec_report_gen_backend.json": GEN}))
        self.assertTrue(got["summary"]["generative"])

    def test_fail_closed_sem_gh(self):
        self.assertIsNone(perimeter.fetch_perimeter_summary(
            "g3-backend-builder", runner=lambda a, **k: None))

    def test_fail_closed_sem_run_de_evento_confiavel(self):
        pr_run = dict(GREEN_RUN, event="pull_request")   # run de PR não é perímetro
        self.assertIsNone(perimeter.fetch_perimeter_summary(
            "g3-backend-builder", runner=_runner([pr_run], {"exec_report_backend.json": REPLAY})))

    def test_fail_closed_run_velho(self):
        old = dict(GREEN_RUN, createdAt="2026-01-01T00:00:00Z")
        self.assertIsNone(perimeter.fetch_perimeter_summary(
            "g3-backend-builder", runner=_runner([old], {"exec_report_backend.json": REPLAY})))

    def test_fail_closed_download_falha(self):
        self.assertIsNone(perimeter.fetch_perimeter_summary(
            "g3-backend-builder", runner=_runner([GREEN_RUN], files=None)))

    def test_fail_closed_artifact_sem_o_agente(self):
        outro = dict(REPLAY, agent_id="g3-frontend-builder")
        self.assertIsNone(perimeter.fetch_perimeter_summary(
            "g3-backend-builder", runner=_runner([GREEN_RUN], {"exec_report_frontend.json": outro})))


class G7PerimeterTest(unittest.TestCase):
    def _gate(self, req, fetched):
        with mock.patch.object(perimeter, "fetch_perimeter_summary", return_value=fetched):
            return promote._gate("G7", {"id": "g3-backend-builder"}, "spec/dir", req, {})

    def test_g7_com_perimetro_usa_o_artefato_e_nomeia_o_run(self):
        ok, ev = self._gate({"delivery_proof": "ci-perimeter"},
                            {"summary": REPLAY, "proof": {"run_id": "123", "commit": "abc123def456",
                                                          "created_at": _now_iso(),
                                                          "workflow": "foundry-exec.yml",
                                                          "artifact": "exec_report_backend.json"}})
        self.assertTrue(ok)
        self.assertIn("perímetro CI: run 123", ev)
        self.assertIn("abc123def456"[:12], ev)

    def test_g7_perimetro_indisponivel_fail_closed_sem_degradar(self):
        ok, ev = self._gate({"delivery_proof": "ci-perimeter"}, None)
        self.assertFalse(ok)
        self.assertIn("PERÍMETRO indisponível", ev)
        self.assertIn("fail-closed", ev)
        self.assertIn("não degrada", ev)


if __name__ == "__main__":
    unittest.main()
