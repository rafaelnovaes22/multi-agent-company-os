"""Integração do DockerExecutor (VERIFY-IN-EVAL F2) — sandbox real.

Roda SÓ onde há Docker + imagem nucleo-exec (job nightly forge-exec.yml, runner Linux).
Localmente (Windows/daemon down) os testes de execução PULAM; a sanitização de paths roda
sempre (não precisa de Docker).

Prova o ganho central da F2: o artefato "plausível-mas-logicamente-errado" passa o oráculo
ESTÁTICO mas FALHA a execução — exatamente o que o F0 não pega.
"""
from __future__ import annotations
import unittest

from nucleo.kernel.execution import DockerExecutor, _safe_files

SEED_TEST = "from app import discount\n\ndef test_discount():\n    assert discount(100, 10) == 90\n"
FIX_OK = {"app.py": "def discount(price, percent):\n    return price - price * percent / 100\n",
          "test_app.py": SEED_TEST}
PLAUSIVEL_ERRADO = {"app.py": "def discount(price, percent):\n    return price - percent / 100\n",
                    "test_app.py": SEED_TEST}


class SanitizacaoDePaths(unittest.TestCase):
    """Roda sempre — o eval-case é canal não-confiável."""
    def test_rejeita_paths_inseguros(self):
        self.assertIsNone(_safe_files({"../escape.py": "x"}))
        self.assertIsNone(_safe_files({"/etc/passwd": "x"}))
        self.assertIsNone(_safe_files({"C:\\win.py": "x"}))
        self.assertIsNone(_safe_files({}))

    def test_aceita_paths_relativos_simples(self):
        self.assertEqual(_safe_files({"app.py": "x", "pkg/mod.py": "y"}),
                         {"app.py": "x", "pkg/mod.py": "y"})


class _DockerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex = DockerExecutor()
        if not cls.ex.available:
            raise unittest.SkipTest("Docker indisponível — execução real só roda no nightly Linux")
        # confirma que a imagem responde; se erro de infra (None), pula em vez de falhar.
        probe = cls.ex.run_tests(dict(FIX_OK), test_cmd="python -m pytest -q")
        if probe is None:
            raise unittest.SkipTest("imagem de execução ausente/infra — pulando integração")
        cls._probe = probe

    def test_fix_correto_passa_execucao(self):
        self.assertIs(self.ex.run_tests(dict(FIX_OK), test_cmd="python -m pytest -q"), True)

    def test_plausivel_errado_falha_execucao(self):
        # passa o estático (não testado aqui), mas a EXECUÇÃO reprova — o ganho da F2
        self.assertIs(self.ex.run_tests(dict(PLAUSIVEL_ERRADO), test_cmd="python -m pytest -q"), False)

    def test_sem_rede_no_container(self):
        # --network none: tentar abrir conexão falha ⇒ teste reprova (exit != 0)
        files = {"test_net.py": "import urllib.request\n\ndef test_net():\n"
                 "    urllib.request.urlopen('http://example.com', timeout=3)\n"}
        self.assertIs(self.ex.run_tests(files, test_cmd="python -m pytest -q"), False)

    def test_natureza_build_heldout_injetado(self):
        # F3: verify_code injeta o held-out do oráculo e executa de verdade — a implementação
        # correta credita delivered; a plausível-mas-errada cai SÓ aqui.
        from nucleo.kernel.verification import verify_code, sha
        contract = "# Contrato: total = soma de price*qty.\n"
        seed = {"orders.py": "def create_order(items):\n    raise NotImplementedError  # TODO\n",
                "docs/contract.md": contract}
        oracle = {
            "bug_file": "orders.py",
            "protected_files": {"docs/contract.md": sha(contract)},
            "bug_markers": {"must_remove": ["NotImplementedError"],
                            "must_contain": ["def create_order"]},
            "heldout_files": {"test_orders.py": (
                "from orders import create_order\n\ndef test_total():\n"
                "    assert create_order([{'price': 10.0, 'qty': 2}])['total'] == 20.0\n")},
            "test_cmd": "python -m pytest -q",
        }
        ok = {"files": {"orders.py": (
            "def create_order(items):\n"
            "    return {'total': sum(i['price'] * i['qty'] for i in items)}\n")}}
        plausivel = {"files": {"orders.py": (
            "def create_order(items):\n"
            "    return {'total': sum(i['price'] for i in items)}\n")}}
        r_ok = verify_code(ok, seed, oracle, executor=self.ex)
        self.assertTrue(r_ok["static_ok"])
        self.assertTrue(r_ok["delivered_ok"])
        r_plaus = verify_code(plausivel, seed, oracle, executor=self.ex)
        self.assertTrue(r_plaus["static_ok"])
        self.assertIs(r_plaus["tests_pass"], False)
        self.assertFalse(r_plaus["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
