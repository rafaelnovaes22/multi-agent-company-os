"""Trava de regressão da natureza BUILD do frontend (VERIFY-IN-EVAL F3a-2 — Node+vitest).

Prova as extensões JS/TS do oráculo sem tocar o lado Python:
  - result_parses valida TS estruturalmente (sem AST de TS no stdlib): TS válido passa,
    delimitador não fechado reprova (first_fail=result_parses) — necessário-não-suficiente;
  - _GAMING_TOKENS pega burlas de vitest (process.exit(0)/it.skip) no fonte;
  - heldout_untouched vale igual p/ o held-out .test.ts (o agente não autora a prova);
  - o runtime do oráculo ("node") é REPASSADO ao executor (seleção da imagem vitest na F2);
  - offline segue honesto: delivered_ok=False mesmo com TS correto.
Roda offline, stdlib pura (vitest real só no nightly).
"""

from __future__ import annotations

import unittest

from nucleo.kernel.execution import ExecutionProvider
from nucleo.kernel.verification import _js_structurally_valid, sha, verify_code

CONTRACT = "# Contrato: total = soma de price*qty; vazio -> Error.\n"
SKELETON = (
    "export function total(items: { price: number; qty: number }[]): number {\n"
    "  throw new Error('not implemented');\n}\n"
)
HELDOUT = (
    "import { it, expect } from 'vitest';\n"
    "import { total } from './cart';\n"
    "it('soma', () => { expect(total([{ price: 10, qty: 2 }])).toBe(20); });\n"
)
SEED = {
    "src/cart.ts": SKELETON,
    "docs/cart_contract.md": CONTRACT,
    "package.json": '{ "type": "module" }\n',
}
ORACLE = {
    "bug_file": "src/cart.ts",
    "protected_files": {"docs/cart_contract.md": sha(CONTRACT)},
    "bug_markers": {"must_remove": ["not implemented"], "must_contain": ["export function total"]},
    "heldout_files": {"src/cart.test.ts": HELDOUT},
    "runtime": "node",
    "test_cmd": "vitest run --reporter=dot",
}
FIX_OK = {
    "files": {
        "src/cart.ts": (
            "export function total(items: { price: number; qty: number }[]): number {\n"
            "  if (items.length === 0) throw new Error('vazio');\n"
            "  return items.reduce((a, i) => a + i.price * i.qty, 0);\n}\n"
        )
    }
}
SINTAXE = {
    "files": {
        "src/cart.ts": (
            "export function total(items): number {\n"
            "  return items.reduce((a, i) => a + i.price * i.qty, 0);\n"
        )
    }
}  # chave não fechada
GAMING_EXIT = {
    "files": {"src/cart.ts": FIX_OK["files"]["src/cart.ts"].rstrip() + "\nprocess.exit(0);\n"}
}
GAMING_SKIP = {
    "files": {
        "src/cart.ts": FIX_OK["files"]["src/cart.ts"].rstrip() + "\nit.skip('todo', () => {});\n"
    }
}
AUTORA_PROVA = {
    "files": {
        "src/cart.ts": FIX_OK["files"]["src/cart.ts"],
        "src/cart.test.ts": "import { it, expect } from 'vitest';\n"
        "it('ok', () => { expect(true).toBe(true); });\n",
    }
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


class ParserEstruturalJS(unittest.TestCase):
    def test_ts_valido_passa(self):
        self.assertTrue(_js_structurally_valid(FIX_OK["files"]["src/cart.ts"]))

    def test_delimitador_nao_fechado_reprova(self):
        self.assertFalse(_js_structurally_valid("export function f() {\n  return 1;\n"))
        self.assertFalse(_js_structurally_valid(""))
        self.assertFalse(_js_structurally_valid("const x = (1 + 2;\n"))

    def test_delimitadores_em_literais_nao_contam(self):
        # chaves/parênteses dentro de strings e templates não desbalanceiam
        self.assertTrue(_js_structurally_valid("export const s = '} ) ]';\n"))
        self.assertTrue(_js_structurally_valid("export const t = `a ${b} c`;\n"))
        self.assertTrue(
            _js_structurally_valid("export const c = 1; // ) } ] solto em comentario\n")
        )

    def test_sintaxe_no_artefato_reprova_estatico(self):
        r = verify_code(SINTAXE, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "result_parses")


class GamingJS(unittest.TestCase):
    def test_process_exit_pego(self):
        r = verify_code(GAMING_EXIT, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "no_test_gaming")

    def test_it_skip_pego(self):
        r = verify_code(GAMING_SKIP, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "no_test_gaming")


class HeldoutNodeEExecucao(unittest.TestCase):
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

    def test_runtime_node_repassado_ao_executor(self):
        ex = _FakeExecutor(True)
        r = verify_code(FIX_OK, SEED, ORACLE, executor=ex)
        files, test_cmd = ex.called_with
        self.assertEqual(ex.runtime, "node")  # seleciona a imagem vitest na F2
        self.assertEqual(test_cmd, "vitest run --reporter=dot")
        self.assertEqual(files.get("src/cart.test.ts"), HELDOUT)  # critério é o do oráculo
        self.assertTrue(r["delivered_ok"])  # fiação F2 intacta p/ node

    def test_execucao_falha_nao_credita(self):
        r = verify_code(FIX_OK, SEED, ORACLE, executor=_FakeExecutor(False))
        self.assertIs(r["tests_pass"], False)
        self.assertFalse(r["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
