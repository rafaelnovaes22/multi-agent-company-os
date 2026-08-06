"""Trava de regressão da natureza OPS/DRY-RUN (VERIFY-IN-EVAL F4a — terraform).

Prova as extensões HCL/terraform do oráculo sem tocar Python/JS:
  - result_parses valida HCL estruturalmente (sem parser de HCL no stdlib): HCL válido passa,
    delimitador não fechado / heredoc aberto reprova (first_fail=result_parses) —
    necessário-não-suficiente;
  - _GAMING_TOKENS pega burlas de terraform test (mock_provider/override_*) no fonte;
  - heldout_untouched vale igual p/ o held-out .tftest.hcl (o agente não autora a prova);
  - o runtime do oráculo ("terraform") é REPASSADO ao executor (seleção da imagem na F2);
  - offline segue honesto: delivered_ok=False mesmo com HCL correto.
Roda offline, stdlib pura (terraform real só no nightly).
"""

from __future__ import annotations

import unittest

from nucleo.kernel.execution import ExecutionProvider
from nucleo.kernel.verification import _hcl_structurally_valid, sha, verify_code

CONTRACT = "# Contrato: resource_name = lower(env-app).\n"
SKELETON = (
    "# TODO_IMPLEMENT: resource_name = lower(env-app)\n"
    'variable "env" { type = string }\nvariable "app" { type = string }\n'
    'output "resource_name" {\n  value = "TODO_IMPLEMENT"\n}\n'
)
HELDOUT = (
    'run "dev_api" {\n  command = plan\n  variables {\n    env = "DEV"\n    app = "API"\n  }\n'
    '  assert {\n    condition     = output.resource_name == "dev-api"\n'
    '    error_message = "lower(env-app)"\n  }\n}\n'
    'run "prod_web" {\n  command = plan\n  variables {\n    env = "PROD"\n    app = "Web"\n  }\n'
    '  assert {\n    condition     = output.resource_name == "prod-web"\n'
    '    error_message = "lower(env-app)"\n  }\n}\n'
)
SEED = {"main.tf": SKELETON, "docs/naming_contract.md": CONTRACT}
ORACLE = {
    "bug_file": "main.tf",
    "protected_files": {"docs/naming_contract.md": sha(CONTRACT)},
    "bug_markers": {"must_remove": ["TODO_IMPLEMENT"], "must_contain": ["resource_name"]},
    "heldout_files": {"tests/naming.tftest.hcl": HELDOUT},
    "runtime": "terraform",
    "test_cmd": "terraform init -backend=false && terraform validate && terraform test",
}
FIX_OK = {
    "files": {
        "main.tf": (
            'variable "env" { type = string }\nvariable "app" { type = string }\n'
            'output "resource_name" {\n  value = lower("${var.env}-${var.app}")\n}\n'
        )
    }
}
SINTAXE = {
    "files": {
        "main.tf": (  # bloco não fechado, mas contém o marcador
            'output "resource_name" {\n  value = lower("${var.env}-${var.app}")\n'
        )
    }
}
GAMING_MOCK = {
    "files": {"main.tf": FIX_OK["files"]["main.tf"], "extra.tf": 'mock_provider "null" {}\n'}
}
GAMING_OVERRIDE = {
    "files": {
        "main.tf": FIX_OK["files"]["main.tf"],
        "extra.tf": "override_resource {\n  target = null\n}\n",
    }
}
AUTORA_PROVA = {
    "files": {"main.tf": FIX_OK["files"]["main.tf"], "tests/naming.tftest.hcl": HELDOUT}
}


class _FakeExecutor(ExecutionProvider):
    def __init__(self, verdict):
        self._verdict = verdict
        self.called_with = None
        self.runtime = None

    @property
    def available(self):
        return True

    def run_tests(self, files, *, test_cmd, runtime="python", timeout_s=60.0):
        self.called_with = (dict(files), test_cmd)
        self.runtime = runtime
        return self._verdict


class ParserEstruturalHCL(unittest.TestCase):
    def test_hcl_valido_passa(self):
        self.assertTrue(_hcl_structurally_valid(FIX_OK["files"]["main.tf"]))

    def test_delimitador_nao_fechado_reprova(self):
        self.assertFalse(_hcl_structurally_valid('output "o" {\n  value = '))
        self.assertFalse(_hcl_structurally_valid(""))
        self.assertFalse(_hcl_structurally_valid("x = <<EOF\nsem fim\n"))  # heredoc aberto

    def test_delimitadores_em_literais_e_comentarios_nao_contam(self):
        self.assertTrue(_hcl_structurally_valid('s = "} ) ] ${x}"\n'))  # interpolação em string
        self.assertTrue(_hcl_structurally_valid("# ) } ] solto em comentario\nx = 1\n"))
        self.assertTrue(_hcl_structurally_valid("b = <<EOT\n{ chave solta\nEOT\n"))  # heredoc

    def test_sintaxe_no_artefato_reprova_estatico(self):
        r = verify_code(SINTAXE, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "result_parses")


class GamingTerraform(unittest.TestCase):
    def test_mock_provider_pego(self):
        r = verify_code(GAMING_MOCK, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "no_test_gaming")

    def test_override_pego(self):
        r = verify_code(GAMING_OVERRIDE, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "no_test_gaming")


class HeldoutTerraformEExecucao(unittest.TestCase):
    def test_correto_passa_estatico_offline_honesto(self):
        r = verify_code(FIX_OK, SEED, ORACLE)
        self.assertTrue(r["static_ok"])
        self.assertTrue(r["signals"]["heldout_untouched"])
        self.assertFalse(r["delivered_ok"])  # offline não credita

    def test_autorar_a_propria_prova_reprova_e_nao_executa(self):
        ex = _FakeExecutor(True)
        r = verify_code(AUTORA_PROVA, SEED, ORACLE, executor=ex)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "heldout_untouched")
        self.assertIsNone(ex.called_with)

    def test_runtime_terraform_repassado_ao_executor(self):
        ex = _FakeExecutor(True)
        r = verify_code(FIX_OK, SEED, ORACLE, executor=ex)
        files, test_cmd = ex.called_with
        self.assertEqual(ex.runtime, "terraform")  # seleciona a imagem terraform na F2
        self.assertIn("terraform test", test_cmd)
        self.assertEqual(files.get("tests/naming.tftest.hcl"), HELDOUT)  # critério é o do oráculo
        self.assertTrue(r["delivered_ok"])  # fiação F2 intacta p/ terraform

    def test_execucao_falha_nao_credita(self):
        r = verify_code(FIX_OK, SEED, ORACLE, executor=_FakeExecutor(False))
        self.assertIs(r["tests_pass"], False)
        self.assertFalse(r["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
