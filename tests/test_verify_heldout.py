"""Trava de regressão da natureza BUILD do oráculo (VERIFY-IN-EVAL F3 — held-out tests).

Prova as garantias novas do g3-backend-builder sem quebrar o red→green do piloto:
  - o critério (testes) vem de `oracle.heldout_files` e NÃO existe na semente;
  - artefato que DECLARA o path de um held-out reprova no estático (heldout_untouched)
    e NUNCA chega a executar — o agente não autora a própria prova;
  - na execução, os held-out são injetados POR CIMA do merge (o que roda é a versão do
    oráculo, jamais a do artefato);
  - oráculo SEM heldout_files (red→green do piloto) segue intacto: heldout_untouched=True.
Roda offline, stdlib pura (executor real só no nightly).
"""
from __future__ import annotations
import unittest

from nucleo.kernel.verification import verify_code, sha
from nucleo.kernel.execution import ExecutionProvider

SKELETON = ("def quote(subtotal, coupon=None):\n"
            "    raise NotImplementedError  # TODO\n")
CONTRACT = "# Contrato: desconto percentual; cupom desconhecido -> KeyError.\n"
HELDOUT_TEST = ("from pricing import quote\n\n"
                "def test_cupom_percentual():\n"
                "    assert quote(200.0, 'SAVE25') == 150.0\n")
SEED = {"pricing.py": SKELETON, "docs/pricing_contract.md": CONTRACT}
ORACLE = {
    "bug_file": "pricing.py",
    "protected_files": {"docs/pricing_contract.md": sha(CONTRACT)},
    "bug_markers": {"must_remove": ["NotImplementedError"], "must_contain": ["def quote"]},
    "heldout_files": {"test_pricing.py": HELDOUT_TEST},
    "test_cmd": "python -m pytest -q",
}
IMPL_OK = {"files": {"pricing.py": (
    "COUPONS = {'SAVE10': 10, 'SAVE25': 25}\n\n"
    "def quote(subtotal, coupon=None):\n"
    "    if coupon is None:\n"
    "        return subtotal\n"
    "    return subtotal - subtotal * COUPONS[coupon] / 100\n")}}
AUTORA_PROVA = {"files": {"pricing.py": IMPL_OK["files"]["pricing.py"],
                          "test_pricing.py": "def test_ok():\n    assert True\n"}}


class _FakeExecutor(ExecutionProvider):
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


class HeldoutEstatico(unittest.TestCase):
    def test_implementacao_correta_passa_estatico(self):
        r = verify_code(IMPL_OK, SEED, ORACLE)
        self.assertTrue(r["static_ok"])
        self.assertTrue(r["signals"]["heldout_untouched"])
        self.assertFalse(r["delivered_ok"])  # offline segue honesto

    def test_autorar_a_propria_prova_reprova(self):
        r = verify_code(AUTORA_PROVA, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "heldout_untouched")

    def test_autorar_a_propria_prova_nunca_executa(self):
        ex = _FakeExecutor(True)
        r = verify_code(AUTORA_PROVA, SEED, ORACLE, executor=ex)
        self.assertIsNone(ex.called_with, "artefato que declara held-out não pode executar")
        self.assertEqual(r["tests_pass"], "UNVERIFIED")
        self.assertFalse(r["delivered_ok"])

    def test_sem_heldout_compat_red_green(self):
        # oráculo do piloto (sem heldout_files): sinal trivialmente True, nada muda
        oracle_f0 = {k: v for k, v in ORACLE.items() if k != "heldout_files"}
        r = verify_code(IMPL_OK, SEED, oracle_f0)
        self.assertTrue(r["signals"]["heldout_untouched"])
        self.assertTrue(r["static_ok"])


class HeldoutInjetadoNaExecucao(unittest.TestCase):
    def test_heldout_do_oraculo_roda_na_execucao(self):
        ex = _FakeExecutor(True)
        r = verify_code(IMPL_OK, SEED, ORACLE, executor=ex)
        files, test_cmd = ex.called_with
        # o critério executado é o DO ORÁCULO, injetado por cima do merge
        self.assertEqual(files.get("test_pricing.py"), HELDOUT_TEST)
        self.assertEqual(test_cmd, "python -m pytest -q")
        # e a execução verde credita delivered (fiação F2 intacta na natureza build)
        self.assertTrue(r["delivered_ok"])

    def test_execucao_falha_nao_credita(self):
        r = verify_code(IMPL_OK, SEED, ORACLE, executor=_FakeExecutor(False))
        self.assertIs(r["tests_pass"], False)
        self.assertFalse(r["delivered_ok"])


if __name__ == "__main__":
    unittest.main()
