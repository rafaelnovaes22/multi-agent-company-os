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


class _DockerNodeIntegration(unittest.TestCase):
    """Natureza BUILD do frontend (F3a-2): execução real com vitest na imagem node.
    Roda só no nightly (forge-exec.yml) com a imagem nucleo-exec-node; pula localmente
    sem Docker/imagem. Exige EXEC_IMAGE_NODE apontando p/ a imagem construída."""

    CART_HELDOUT = ("import { it, expect } from 'vitest';\n"
                    "import { total } from './cart';\n"
                    "it('soma price*qty', () => { expect(total([{ price: 10, qty: 2 }])).toBe(20); });\n")
    FIX = ("export function total(items) {\n"
           "  if (items.length === 0) throw new Error('vazio');\n"
           "  return items.reduce((a, i) => a + i.price * i.qty, 0);\n}\n")
    PLAUSIVEL = ("export function total(items) {\n"
                 "  if (items.length === 0) throw new Error('vazio');\n"
                 "  return items.reduce((a, i) => a + i.price, 0);\n}\n")  # ignora qty

    @classmethod
    def setUpClass(cls):
        cls.ex = DockerExecutor()
        if not cls.ex.available:
            raise unittest.SkipTest("Docker indisponível — execução vitest só roda no nightly Linux")
        files = {"src/cart.ts": cls.FIX, "src/cart.test.ts": cls.CART_HELDOUT,
                 "package.json": '{ "type": "module" }\n'}
        probe = cls.ex.run_tests(files, test_cmd="vitest run --reporter=dot", runtime="node")
        if probe is None:
            raise unittest.SkipTest("imagem node ausente/infra — pulando integração vitest")
        cls._files = files

    def test_fix_correto_passa_vitest(self):
        self.assertIs(self.ex.run_tests(dict(self._files),
                      test_cmd="vitest run --reporter=dot", runtime="node"), True)

    def test_plausivel_errado_falha_vitest(self):
        files = dict(self._files)
        files["src/cart.ts"] = self.PLAUSIVEL
        # passa o estático mas a EXECUÇÃO (held-out de soma) reprova — o ganho da F2 no node
        self.assertIs(self.ex.run_tests(files, test_cmd="vitest run --reporter=dot",
                                        runtime="node"), False)

    def test_natureza_build_node_via_verify_code(self):
        from nucleo.kernel.verification import verify_code, sha
        contract = "# Contrato: total = soma price*qty.\n"
        seed = {"src/cart.ts": "export function total(items) {\n  throw new Error('not implemented');\n}\n",
                "docs/c.md": contract, "package.json": '{ "type": "module" }\n'}
        oracle = {
            "bug_file": "src/cart.ts",
            "protected_files": {"docs/c.md": sha(contract)},
            "bug_markers": {"must_remove": ["not implemented"], "must_contain": ["export function total"]},
            "heldout_files": {"src/cart.test.ts": self.CART_HELDOUT},
            "runtime": "node", "test_cmd": "vitest run --reporter=dot"}
        ok = verify_code({"files": {"src/cart.ts": self.FIX}}, seed, oracle, executor=self.ex)
        self.assertTrue(ok["static_ok"])
        self.assertTrue(ok["delivered_ok"])
        plaus = verify_code({"files": {"src/cart.ts": self.PLAUSIVEL}}, seed, oracle, executor=self.ex)
        self.assertTrue(plaus["static_ok"])
        self.assertIs(plaus["tests_pass"], False)
        self.assertFalse(plaus["delivered_ok"])


class _DockerTerraformIntegration(unittest.TestCase):
    """Natureza OPS/DRY-RUN (F4a): execução real com `terraform test` (command=plan) na imagem
    terraform. SEM providers de cloud ⇒ --network none não atrapalha. Roda só no nightly
    (forge-exec.yml) com nucleo-exec-terraform; pula localmente sem Docker/imagem."""

    HELDOUT = (
        'run "dev_api" {\n  command = plan\n  variables {\n    env = "DEV"\n    app = "API"\n  }\n'
        '  assert {\n    condition     = output.resource_name == "dev-api"\n'
        '    error_message = "lower(env-app)"\n  }\n}\n'
        'run "prod_web" {\n  command = plan\n  variables {\n    env = "PROD"\n    app = "Web"\n  }\n'
        '  assert {\n    condition     = output.resource_name == "prod-web"\n'
        '    error_message = "lower(env-app)"\n  }\n}\n')
    FIX = ('variable "env" { type = string }\nvariable "app" { type = string }\n'
           'output "resource_name" {\n  value = lower("${var.env}-${var.app}")\n}\n')
    PLAUSIVEL = ('variable "env" { type = string }\nvariable "app" { type = string }\n'
                 'output "resource_name" {\n  value = "${var.env}-${var.app}"\n}\n')  # sem lower()
    TEST_CMD = "terraform init -backend=false && terraform validate && terraform test"

    @classmethod
    def setUpClass(cls):
        cls.ex = DockerExecutor()
        if not cls.ex.available:
            raise unittest.SkipTest("Docker indisponível — terraform test só roda no nightly Linux")
        files = {"main.tf": cls.FIX, "tests/naming.tftest.hcl": cls.HELDOUT}
        probe = cls.ex.run_tests(files, test_cmd=cls.TEST_CMD, runtime="terraform")
        if probe is None:
            raise unittest.SkipTest("imagem terraform ausente/infra — pulando integração")

    def test_fix_correto_passa_terraform_test(self):
        files = {"main.tf": self.FIX, "tests/naming.tftest.hcl": self.HELDOUT}
        self.assertIs(self.ex.run_tests(files, test_cmd=self.TEST_CMD, runtime="terraform"), True)

    def test_plausivel_errado_falha_terraform_test(self):
        files = {"main.tf": self.PLAUSIVEL, "tests/naming.tftest.hcl": self.HELDOUT}
        # passa o estático, mas a EXECUÇÃO (held-out com 2 inputs) reprova — o ganho da F4a
        self.assertIs(self.ex.run_tests(files, test_cmd=self.TEST_CMD, runtime="terraform"), False)

    def test_natureza_ops_via_verify_code(self):
        from nucleo.kernel.verification import verify_code, sha
        contract = "# Contrato: resource_name = lower(env-app).\n"
        seed = {"main.tf": 'output "resource_name" {\n  value = "TODO_IMPLEMENT"\n}\n',
                "docs/c.md": contract}
        oracle = {
            "bug_file": "main.tf",
            "protected_files": {"docs/c.md": sha(contract)},
            "bug_markers": {"must_remove": ["TODO_IMPLEMENT"], "must_contain": ["resource_name"]},
            "heldout_files": {"tests/naming.tftest.hcl": self.HELDOUT},
            "runtime": "terraform", "test_cmd": self.TEST_CMD}
        ok = verify_code({"files": {"main.tf": self.FIX}}, seed, oracle, executor=self.ex)
        self.assertTrue(ok["static_ok"])
        self.assertTrue(ok["delivered_ok"])
        plaus = verify_code({"files": {"main.tf": self.PLAUSIVEL}}, seed, oracle, executor=self.ex)
        self.assertTrue(plaus["static_ok"])
        self.assertIs(plaus["tests_pass"], False)
        self.assertFalse(plaus["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
