"""Trava de regressão do oráculo VERIFY-IN-EVAL F0 (verify_code + handler spec_executor).

Prova a ACEITAÇÃO-CHAVE do F0: o eval REPROVA o "fix que deleta o teste-alvo" e APROVA o
fix correto — distinção que o generic_contract_grader (contrato) NÃO faz. E crava o limite
honesto: offline `delivered_ok` é SEMPRE False (sem executar não se afirma correção).
Roda offline, stdlib pura.
"""

from __future__ import annotations

import unittest

from nucleo.kernel.providers.llm import FakeLLMProvider
from nucleo.kernel.skills_exec import spec_executor
from nucleo.kernel.verification import sha, verify_code
from nucleo.quality.graders import generic_contract_grader

SEED = {
    "app.py": "def discount(price, percent):\n    return price - price * pct / 100\n",
    "test_app.py": "from app import discount\n\ndef test_discount():\n    assert discount(100, 10) == 90\n",
}
ORACLE = {
    "bug_file": "app.py",
    "protected_files": {"test_app.py": sha(SEED["test_app.py"])},
    "bug_markers": {"must_remove": ["pct"], "must_contain": ["percent"]},
}
FIX_OK = {
    "files": {"app.py": "def discount(price, percent):\n    return price - price * percent / 100\n"}
}
DELETA = {"files": {"app.py": FIX_OK["files"]["app.py"], "test_app.py": "def t():\n    pass\n"}}
GAMING = {
    "files": {
        "app.py": "import sys\ndef discount(price, percent):\n    sys.exit(0)\n    return price * percent\n"
    }
}
SINTAXE = {"files": {"app.py": "def discount(price, percent)\n    return percent\n"}}
TEXTO = {
    "content": "Eu corrigiria a variável...",
    "rationale": "x",
    "by": "g3-build-error-resolver",
}
PLAUSIVEL = {
    "files": {"app.py": "def discount(price, percent):\n    return price - percent / 100\n"}
}


def _run(artifact):
    state = {"task": {"artifact": artifact, "seed": SEED, "oracle": ORACLE}}
    return spec_executor(
        state, llm=FakeLLMProvider(), store=None, spec={"id": "g3-build-error-resolver"}
    )["output"]


class VerifyCodeOracle(unittest.TestCase):
    def test_aprova_fix_correto(self):
        r = verify_code(FIX_OK, SEED, ORACLE)
        self.assertTrue(r["static_ok"])
        self.assertIsNone(r["first_fail"])

    def test_reprova_deleta_teste_alvo(self):
        r = verify_code(DELETA, SEED, ORACLE)
        self.assertFalse(r["static_ok"])
        self.assertEqual(r["first_fail"], "protected_unmodified")

    def test_reprova_gaming_sintaxe_texto(self):
        self.assertEqual(verify_code(GAMING, SEED, ORACLE)["first_fail"], "no_test_gaming")
        self.assertEqual(verify_code(SINTAXE, SEED, ORACLE)["first_fail"], "result_parses")
        self.assertEqual(verify_code(TEXTO, SEED, ORACLE)["first_fail"], "artifact_parseable")

    def test_delivered_sempre_false_offline(self):
        # mesmo o fix correto NÃO é "delivered" offline — não executou (honesto)
        self.assertFalse(verify_code(FIX_OK, SEED, ORACLE)["delivered_ok"])

    def test_limite_honesto_plausivel_passa_estatico(self):
        # fix plausível mas logicamente errado passa o estático; só F2 (execução) o pegaria
        r = verify_code(PLAUSIVEL, SEED, ORACLE)
        self.assertTrue(r["static_ok"])
        self.assertFalse(r["delivered_ok"])


class HandlerDistingueOndeContratoNaoDistingue(unittest.TestCase):
    def test_handler_static_ok_difere(self):
        self.assertTrue(_run(FIX_OK)["static_ok"])
        self.assertFalse(_run(DELETA)["static_ok"])
        self.assertEqual(_run(DELETA)["status"], "rejected:protected_unmodified")

    def test_contrato_antigo_seria_cego(self):
        # sob o grader de contrato, os dois outputs (mesmo handler_kind/by/rationale) passariam
        # o mesmo `expected` de contrato — o gap exato que o oráculo fecha.
        contrato = {"handler_kind": "spec_executor", "by": "g3-build-error-resolver"}
        self.assertTrue(generic_contract_grader(_run(FIX_OK), contrato))
        self.assertTrue(generic_contract_grader(_run(DELETA), contrato))
        # mas o grader específico (spec_executor) os separa via static_ok:
        self.assertNotEqual(_run(FIX_OK)["static_ok"], _run(DELETA)["static_ok"])


if __name__ == "__main__":
    unittest.main()
