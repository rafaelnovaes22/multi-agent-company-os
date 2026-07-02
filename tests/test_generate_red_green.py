"""Travas do gerador red→green (épico VERIFY-IN-EVAL, fase geradora — plano §4.7).

O que estes testes garantem (offline, LLM roteirizado + executor fake):
  1. o loop itera: red na 1ª tentativa (feedback com o erro vai ao prompt) → green na 2ª;
  2. o HELD-OUT nunca vaza: conteúdo held-out jamais aparece em prompt algum, e patch em
     path held-out é descartado (autor != provador);
  3. budget: para em GEN_MAX_ITERS quando tudo é red;
  4. resposta não-JSON gera feedback e nova tentativa, não crash;
  5. sem executor real: one-shot honesto (loop_green=False, sem execução);
  6. erro de infra (None) não itera às cegas;
  7. run_generative mede SÓ os elegíveis e publica delivered_eligible_rate generativo.
"""
from __future__ import annotations

import json
import unittest

from nucleo.kernel.generate import generate_red_green, _extract_files
from nucleo.quality import exec_report

SECRET = "HELDOUT_SECRET_TOKEN_XYZ"

SEED = {"app.py": "def soma(a, b):\n    return a - b\n",
        "test_app.py": "from app import soma\n\ndef test_soma():\n    assert soma(2, 2) == 4\n"}
ORACLE = {"bug_file": "app.py", "runtime": "python", "test_cmd": "pytest -q",
          "heldout_files": {"test_held.py": f"# {SECRET}\nfrom app import soma\n"
                                            f"def test_h():\n    assert soma(1, 1) == 2\n"}}
GOOD = json.dumps({"files": {"app.py": "def soma(a, b):\n    return a + b\n"}})
BAD = json.dumps({"files": {"app.py": "def soma(a, b):\n    return a * b\n"}})


class ScriptedLLM:
    """Devolve respostas em sequência e captura todos os prompts recebidos."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    @property
    def name(self):
        return "ScriptedLLM"

    def complete(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.responses.pop(0) if self.responses else "{}"


class ScriptedExecutor:
    """Vereditos em sequência; disponível; registra os arquivos executados."""

    def __init__(self, verdicts, outputs=None):
        self.verdicts = list(verdicts)
        self.outputs = list(outputs or [])
        self.executed_files = []
        self.name = "ScriptedExecutor"

    @property
    def available(self):
        return True

    def run_tests(self, files, *, test_cmd, runtime="python", timeout_s=60.0):
        return self.run_tests_detail(files, test_cmd=test_cmd, runtime=runtime)["passed"]

    def run_tests_detail(self, files, *, test_cmd, runtime="python", timeout_s=60.0):
        self.executed_files.append(dict(files))
        verdict = self.verdicts.pop(0) if self.verdicts else None
        output = self.outputs.pop(0) if self.outputs else ""
        return {"passed": verdict, "output": output}


class RedGreenLoopTest(unittest.TestCase):
    def test_red_depois_green_com_feedback_no_prompt(self):
        llm = ScriptedLLM([BAD, GOOD])
        ex = ScriptedExecutor([False, True], outputs=["AssertionError: assert 4 == 4"])
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, ex)
        self.assertTrue(r["loop_green"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["artifact"]["files"]["app.py"], "def soma(a, b):\n    return a + b\n")
        # o erro da execução red alimentou o prompt seguinte
        self.assertIn("AssertionError", llm.prompts[1])

    def test_heldout_jamais_vaza_no_prompt_e_patch_em_heldout_e_descartado(self):
        malicious = json.dumps({"files": {
            "app.py": "def soma(a, b):\n    return a + b\n",
            "test_held.py": "def test_h():\n    assert True\n"}})   # tenta escrever o critério
        llm = ScriptedLLM([malicious])
        ex = ScriptedExecutor([True])
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, ex)
        for prompt in llm.prompts:
            self.assertNotIn(SECRET, prompt)          # conteúdo held-out fora do prompt
            self.assertNotIn("test_held.py", prompt)  # nem o path é anunciado
        self.assertNotIn("test_held.py", r["artifact"]["files"])   # autor != provador
        self.assertEqual(r["history"][0]["dropped_heldout_paths"], ["test_held.py"])
        # e o held-out não entrou na execução VISÍVEL do loop
        self.assertNotIn("test_held.py", ex.executed_files[0])

    def test_reescrever_teste_protegido_nao_vira_green_e_roda_na_versao_da_semente(self):
        # gaming clássico: "conserta" reescrevendo o teste-alvo. O loop tem de (a) executar
        # com a versão da SEMENTE do arquivo protegido, (b) não aceitar green com protegido
        # tocado, (c) devolver feedback nomeando o arquivo. Na 2ª tentativa limpa, green.
        oracle = dict(ORACLE)
        oracle["protected_files"] = {"test_app.py": "sha-qualquer"}
        gaming = json.dumps({"files": {
            "app.py": "def soma(a, b):\n    return a + b\n",
            "test_app.py": "def test_soma():\n    assert True\n"}})
        llm = ScriptedLLM([gaming, GOOD])
        ex = ScriptedExecutor([True, True])
        r = generate_red_green("corrija soma", SEED, oracle, llm, ex)
        self.assertTrue(r["loop_green"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["history"][0]["touched_protected_paths"], ["test_app.py"])
        # (a) a execução da 1ª tentativa usou o teste da SEMENTE, não o reescrito
        self.assertEqual(ex.executed_files[0]["test_app.py"], SEED["test_app.py"])
        # (c) o feedback nomeou o arquivo protegido
        self.assertIn("test_app.py", llm.prompts[1])
        self.assertIn("protegido", llm.prompts[1])

    def test_budget_para_no_max_iters_tudo_red(self):
        llm = ScriptedLLM([BAD] * 10)
        ex = ScriptedExecutor([False] * 10)
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, ex, max_iters=3)
        self.assertFalse(r["loop_green"])
        self.assertEqual(r["attempts"], 3)

    def test_resposta_nao_json_gera_feedback_e_nova_tentativa(self):
        llm = ScriptedLLM(["claro! segue o codigo: def soma...", GOOD])
        ex = ScriptedExecutor([True])
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, ex)
        self.assertTrue(r["loop_green"])
        self.assertEqual(r["attempts"], 2)
        self.assertFalse(r["history"][0]["parsed"])
        self.assertIn("JSON", llm.prompts[1])   # feedback pediu o contrato

    def test_sem_executor_e_one_shot_honesto(self):
        llm = ScriptedLLM([GOOD])
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, None)
        self.assertFalse(r["loop_green"])
        self.assertEqual(r["attempts"], 1)
        self.assertTrue(r["history"][0].get("no_executor"))

    def test_erro_de_infra_nao_itera_as_cegas(self):
        llm = ScriptedLLM([GOOD, GOOD])
        ex = ScriptedExecutor([None])
        r = generate_red_green("corrija soma", SEED, ORACLE, llm, ex)
        self.assertFalse(r["loop_green"])
        self.assertEqual(r["attempts"], 1)   # parou no None, não gastou budget às cegas

    def test_green_executavel_com_estatico_vermelho_nao_fecha_o_loop(self):
        # infra real: terraform validate passa com o marcador TODO ainda no arquivo — o
        # green executável NÃO basta; a sonda estática tem de aprovar antes do loop fechar.
        oracle = dict(ORACLE)
        oracle["bug_markers"] = {"must_remove": ["TODO-MARK"], "must_contain": []}
        seed = dict(SEED)
        seed["app.py"] = "def soma(a, b):\n    return a - b  # TODO-MARK\n"
        marker_left = json.dumps({"files": {"app.py": "def soma(a, b):\n    return a + b  # TODO-MARK\n"}})
        clean = json.dumps({"files": {"app.py": "def soma(a, b):\n    return a + b\n"}})
        llm = ScriptedLLM([marker_left, clean])
        ex = ScriptedExecutor([True, True])   # executável green nas duas
        r = generate_red_green("corrija soma", seed, oracle, llm, ex)
        self.assertTrue(r["loop_green"])
        self.assertEqual(r["attempts"], 2)
        self.assertIs(r["history"][0]["static_ok"], False)
        self.assertIn("bug_addressed", llm.prompts[1])   # feedback nomeou o critério

    def test_semente_sem_teste_visivel_usa_sonda_estatica_sem_executar(self):
        # backend/frontend/mobile: o único teste é o held-out (oculto). O loop não pode
        # executar (rodaria vazio) nem ver o held-out: itera contra a SONDA ESTÁTICA e
        # vaza só o NOME do critério reprovado. O executor não é chamado no loop.
        seed = {"api/orders.py": "def total(items):\n    return 0  # TODO-BUG\n"}
        oracle = {"bug_file": "api/orders.py", "runtime": "python",
                  "test_cmd": "pytest -q",
                  "bug_markers": {"must_remove": ["TODO-BUG"], "must_contain": []},
                  "heldout_files": {"test_orders.py": f"# {SECRET}\n"}}
        still_bad = json.dumps({"files": {"api/orders.py":
                                          "def total(items):\n    # ajuste\n    return 0  # TODO-BUG\n"}})
        good = json.dumps({"files": {"api/orders.py":
                                     "def total(items):\n    return sum(i['price'] * i['qty'] for i in items)\n"}})
        llm = ScriptedLLM([still_bad, good])
        ex = ScriptedExecutor([True] * 5)
        r = generate_red_green("some o carrinho", seed, oracle, llm, ex)
        self.assertEqual(r["attempts"], 2)
        self.assertTrue(r["history"][0]["static_probe"])
        self.assertEqual(r["history"][0]["first_fail"], "bug_addressed")
        self.assertTrue(r["history"][1]["static_ok"])
        self.assertEqual(ex.executed_files, [])          # loop não executou nada
        self.assertIn("bug_addressed", llm.prompts[1])   # feedback = só o nome do critério
        for p in llm.prompts:
            self.assertNotIn(SECRET, p)                  # held-out continua fora

    def test_extract_files_aceita_json_cercado(self):
        text = "Aqui está:\n```json\n" + GOOD + "\n```\nEspero que ajude!"
        self.assertEqual(_extract_files(text),
                         {"app.py": "def soma(a, b):\n    return a + b\n"})


class RunGenerativeTest(unittest.TestCase):
    SPEC_DIR = "nucleo/guilds/g03_engenharia/g3-build-error-resolver"

    def test_mede_so_os_elegiveis_e_publica_taxa_generativa(self):
        cases = json.load(open(f"{self.SPEC_DIR}/evals/cases.json", encoding="utf-8"))
        n_eligible = sum(1 for c in cases if (c.get("expected") or {}).get("exec_delivered"))
        self.assertEqual(n_eligible, 8)

        # LLM que sempre devolve um patch "plausível" qualquer; executor sempre red no loop
        # e red na verificação final ⇒ generativo honesto: 0 delivered em 8 elegíveis.
        llm = ScriptedLLM([BAD] * 200)
        ex = ScriptedExecutor([False] * 200)
        rep = exec_report.run_generative(self.SPEC_DIR, llm=llm, executor=ex)
        self.assertTrue(rep["generative"])
        self.assertEqual(rep["n"], n_eligible)          # negativos-por-design FORA
        summary = exec_report.summarize(rep, executor_name=ex.name, executor_available=True)
        self.assertEqual(summary["delivered_eligible_rate"]["total"], n_eligible)
        self.assertEqual(summary["delivered_eligible_rate"]["passed"], 0)
        self.assertEqual(summary["false_positive_delivery_count"], 0)
        # generativo não asserta o estático do caso: oracle_correct fica fora
        self.assertEqual(summary["oracle_evaluated_count"], 0)

    def test_main_generative_exige_llm_real_quando_pedido(self):
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = exec_report.main(["--generative", "--require-real-llm", self.SPEC_DIR])
        self.assertEqual(code, 2)
        self.assertIn("LLM real", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
