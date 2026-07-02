"""Trava da SEAM de execução (VERIFY-IN-EVAL F1).

Prova que o ponto de injeção de execução está fiado e HONESTO, antes de existir runner real (F2):
  - default (InertExecutor / sem EXEC_PROVIDER) ⇒ tests_pass=UNVERIFIED, delivered_ok=False (= F0).
  - executor que EXECUTA e passa ⇒ delivered_ok=True — SÓ quando o estático também passa.
  - executor que executa e falha ⇒ delivered_ok=False.
  - delivered_ok NUNCA é True sem static_ok, mesmo que a "execução" diga que passou
    (anti verde-por-fixture: tests_pass vem do executor, jamais de um booleano do caso).
Roda offline, sem Docker.
"""
from __future__ import annotations
import os
import unittest
from unittest import mock

from nucleo.kernel.verification import verify_code, sha
from nucleo.kernel import execution as execmod
from nucleo.kernel.execution import InertExecutor, DockerExecutor, get_executor, ExecutionProvider

SEED = {
    "app.py": "def discount(price, percent):\n    return price - price * pct / 100\n",
    "test_app.py": "from app import discount\n\ndef test_discount():\n    assert discount(100, 10) == 90\n",
}
ORACLE = {
    "bug_file": "app.py",
    "protected_files": {"test_app.py": sha(SEED["test_app.py"])},
    "bug_markers": {"must_remove": ["pct"], "must_contain": ["percent"]},
    "test_cmd": "pytest -q",
}
FIX_OK = {"files": {"app.py": "def discount(price, percent):\n    return price - price * percent / 100\n"}}
SINTAXE = {"files": {"app.py": "def discount(price, percent)\n    return percent\n"}}  # static FAIL


class _FakeExecutor(ExecutionProvider):
    """Executor de teste: simula execução real (available=True) com veredito fixo, e REGISTRA
    se foi chamado. Injetado programaticamente — nunca vem do eval-case."""
    def __init__(self, verdict):
        self._verdict = verdict
        self.called_with = None

    @property
    def available(self):
        return True

    def run_tests(self, files, *, test_cmd, runtime="python", timeout_s=60.0):
        self.called_with = (dict(files), test_cmd)
        self.runtime = runtime
        return self._verdict


class InertIsDefault(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("EXEC_PROVIDER", None)

    def tearDown(self):
        # restaura SEMPRE: sem o pop, o "docker" setado num teste vaza p/ o resto da
        # sessão e liga execução real nos testes offline (falha se houver daemon local).
        if self._saved is not None:
            os.environ["EXEC_PROVIDER"] = self._saved
        else:
            os.environ.pop("EXEC_PROVIDER", None)

    def test_get_executor_default_inerte(self):
        ex = get_executor()
        self.assertIsInstance(ex, InertExecutor)
        self.assertFalse(ex.available)

    def test_docker_resolve_para_dockerexecutor(self):
        os.environ["EXEC_PROVIDER"] = "docker"
        self.assertIsInstance(get_executor(), DockerExecutor)

    def test_dockerexecutor_indisponivel_e_unverified(self):
        # sem daemon (available=False) o DockerExecutor NÃO executa ⇒ None (UNVERIFIED),
        # nunca um falso verde. (No nightly Linux+Docker, available=True e executa de fato.)
        ex = DockerExecutor()
        ex._avail = False
        self.assertFalse(ex.available)
        self.assertIsNone(ex.run_tests({"a.py": "x"}, test_cmd="python -m pytest -q"))

    def test_inert_mantem_comportamento_f0(self):
        v = verify_code(FIX_OK, SEED, ORACLE, executor=InertExecutor())
        self.assertTrue(v["static_ok"])
        self.assertEqual(v["tests_pass"], "UNVERIFIED")
        self.assertFalse(v["delivered_ok"])

    def test_sem_executor_igual_inert(self):
        self.assertEqual(verify_code(FIX_OK, SEED, ORACLE)["delivered_ok"], False)


class DockerCommandHardening(unittest.TestCase):
    """Trava a config de sandbox do DockerExecutor SEM precisar de Docker (mock de subprocess).
    Garante que os flags de segurança não regridam silenciosamente."""

    def _captura_cmd(self, files):
        ex = DockerExecutor()
        ex._avail = True  # finge daemon presente p/ chegar na montagem do comando
        fake = mock.Mock(returncode=0, stderr=b"")
        with mock.patch.object(execmod.subprocess, "run", return_value=fake) as m:
            ex.run_tests(files, test_cmd="python -m pytest -q")
        return m.call_args[0][0] if m.call_args else []

    def test_flags_de_seguranca_presentes(self):
        cmd = " ".join(self._captura_cmd({"app.py": "print(1)\n"}))
        for flag in ("--rm", "--network none", "--cap-drop ALL",
                     "--security-opt no-new-privileges", "--read-only",
                     "--pids-limit", "--memory 512m", "--cpus 1"):
            self.assertIn(flag, cmd, f"flag de sandbox ausente: {flag}")

    def test_paths_inseguros_nao_executam(self):
        ex = DockerExecutor()
        ex._avail = True
        with mock.patch.object(execmod.subprocess, "run") as m:
            self.assertIsNone(ex.run_tests({"../x.py": "evil"}, test_cmd="python -m pytest -q"))
            m.assert_not_called()  # nem chega a rodar docker


class ExecutorWiring(unittest.TestCase):
    def test_execucao_passa_credita_delivered(self):
        ex = _FakeExecutor(True)
        v = verify_code(FIX_OK, SEED, ORACLE, executor=ex)
        self.assertTrue(v["static_ok"])
        self.assertTrue(v["tests_pass"])
        self.assertTrue(v["delivered_ok"])
        # executou o repo MERGED (semente + patch), com o comando do oráculo
        self.assertEqual(ex.called_with[1], "pytest -q")
        self.assertIn("app.py", ex.called_with[0])

    def test_execucao_falha_nao_credita(self):
        v = verify_code(FIX_OK, SEED, ORACLE, executor=_FakeExecutor(False))
        self.assertFalse(v["delivered_ok"])
        self.assertIs(v["tests_pass"], False)

    def test_nunca_executa_se_estatico_reprova(self):
        # mesmo um executor que "passaria", se o estático reprova, NÃO executa e não credita
        ex = _FakeExecutor(True)
        v = verify_code(SINTAXE, SEED, ORACLE, executor=ex)
        self.assertFalse(v["static_ok"])
        self.assertEqual(v["first_fail"], "result_parses")
        self.assertIsNone(ex.called_with, "não deve executar artefato que falhou no estático")
        self.assertEqual(v["tests_pass"], "UNVERIFIED")
        self.assertFalse(v["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
