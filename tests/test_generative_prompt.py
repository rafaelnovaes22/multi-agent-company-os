"""Trava de regressão da CAMADA GENERATIVA (PRs #25-#29).

O caminho que de fato roda em CI/SHADOW é o FakeLLMProvider, que IGNORA o prompt —
então 'demo_eval verde' não prova NADA sobre o wiring do prompt generativo. Este teste
fecha esse buraco: com um provider-espião que captura o prompt, prova que

  - a persona (soul.md) entra no prompt            (#28)
  - a cláusula de outcome C2 entra inteira          (#26: statement + ✓/✗ exemplos + delivered)
  - a instrução anti-meta + entrega-agora entra     (#29)
  - max_tokens=4096 é propagado                     (#29)
  - cost_tokens conta ENTRADA (prompt) + SAÍDA      (#27)
  - get_llm é opt-in e cai no offline com aviso      (#25)
  - o provider real re-tenta erros transientes       (#25, robustez desta PR)

Roda offline, sem rede e sem SDK de LLM.
"""

from __future__ import annotations

import logging
import os
import tempfile
import unittest

from nucleo.kernel.providers import llm as llm_mod
from nucleo.kernel.providers.llm import FakeLLMProvider, _with_retry, get_llm
from nucleo.kernel.skills import _SOUL_CACHE, _catalog_agent_output, _tokens

SOUL_TEXT = (
    "Persona: sou cética, exijo evidência. Princípio: não escrevo sem diagnóstico (viola C1)."
)


class _SpyProvider:
    """Captura o último prompt e kwargs; devolve um conteúdo fixo reconhecível."""

    def __init__(self, out="ARTEFATO-CONCRETO-123"):
        self.out = out
        self.prompt = None
        self.kwargs = None

    @property
    def name(self):
        return "SpyProvider"

    def complete(self, prompt, **kwargs):
        self.prompt = prompt
        self.kwargs = kwargs
        return self.out


def _spec(spec_dir):
    return {
        "id": "g99-test-author",
        "guild": "g99",
        "_spec_dir": spec_dir,
        "outcome_clause": {
            "statement": "OUTCOME_C2_MARKER: entregar o documento aprovado.",
            "positive_examples": ["POS_MARKER_doc_completo"],
            "negative_examples": ["NEG_MARKER_so_descreve_processo"],
            "delivered_event": "DELIVERED_MARKER doc.published",
        },
    }


def _state():
    return {
        "task": {
            "statement": "TASK_MARKER: escrever a política X.",
            "artifact_type": "policy.doc",
            "risk": "low",
        },
        "context": {
            "tenant_profile": {"name": "PROFILE_MARKER Ltda"},
            "memory": ["MEMORY_MARKER decisão anterior"],
        },
    }


class GenerativePromptWiring(unittest.TestCase):
    def setUp(self):
        _SOUL_CACHE.clear()
        self._tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(self._tmp.name, "soul.md"), "w", encoding="utf-8") as f:
            f.write(SOUL_TEXT)
        self.spec = _spec(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        _SOUL_CACHE.clear()

    def test_prompt_carrega_soul_c2_e_antimeta(self):
        spy = _SpyProvider()
        out = _catalog_agent_output(_state(), llm=spy, spec=self.spec, handler_kind="spec_driven")
        p = spy.prompt
        self.assertIsNotNone(p, "o handler generativo deveria ter chamado llm.complete")
        # persona (#28)
        self.assertIn("não escrevo sem diagnóstico", p, "soul.md não foi injetado no prompt")
        # C2 completo (#26)
        self.assertIn("OUTCOME_C2_MARKER", p)
        self.assertIn("POS_MARKER_doc_completo", p)
        self.assertIn("NEG_MARKER_so_descreve_processo", p)
        self.assertIn("DELIVERED_MARKER", p)
        # task + contexto do tenant
        self.assertIn("TASK_MARKER", p)
        self.assertIn("PROFILE_MARKER", p)
        self.assertIn("MEMORY_MARKER", p)
        # anti-meta / entrega-agora (#29)
        self.assertIn("ENTREGUE AGORA", p)
        # max_tokens propagado (#29)
        self.assertEqual(spy.kwargs.get("max_tokens"), 4096)
        # o conteúdo gerado vira o artefato (content) e mantém rationale por contrato
        self.assertEqual(out["output"]["content"], spy.out)
        self.assertEqual(out["output"]["rationale"], spy.out)

    def test_cost_conta_entrada_mais_saida(self):
        spy = _SpyProvider(out="x y z")
        out = _catalog_agent_output(_state(), llm=spy, spec=self.spec, handler_kind="spec_driven")
        esperado = _tokens(spy.prompt) + _tokens(spy.out)
        self.assertEqual(
            out["cost_tokens"],
            esperado,
            "cost_tokens deve somar ENTRADA (prompt) + SAÍDA (content) — PR #27",
        )
        # entrada não é desprezível: o prompt rico domina o custo
        self.assertGreater(_tokens(spy.prompt), _tokens(spy.out))

    def test_sem_soul_nao_quebra(self):
        spec = dict(self.spec)
        spec.pop("_spec_dir")
        spy = _SpyProvider()
        out = _catalog_agent_output(_state(), llm=spy, spec=spec, handler_kind="spec_driven")
        self.assertEqual(out["output"]["content"], spy.out)
        self.assertNotIn("não escrevo sem diagnóstico", spy.prompt)


class ProviderSelection(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("LLM_PROVIDER", "LLM_RETRIES")}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_opt_in_default_offline(self):
        self.assertIsInstance(get_llm(), FakeLLMProvider)

    def test_provider_desconhecido_cai_no_offline_com_aviso(self):
        os.environ["LLM_PROVIDER"] = "provider-que-nao-existe"
        with self.assertLogs("nucleo.kernel.providers.llm", level="WARNING"):
            self.assertIsInstance(get_llm(), FakeLLMProvider)

    def test_fallback_loga_quando_construcao_do_provider_real_falha(self):
        # Quando o provider real falha ao instanciar (SDK ausente, config inválida), get_llm
        # NÃO deve propagar — cai no offline e AVISA (não mais 'except: pass' silencioso).
        os.environ["LLM_PROVIDER"] = "anthropic"
        orig = llm_mod.AnthropicProvider
        llm_mod.AnthropicProvider = lambda _model: (_ for _ in ()).throw(
            RuntimeError("sem credencial")
        )
        try:
            with self.assertLogs("nucleo.kernel.providers.llm", level="WARNING"):
                self.assertIsInstance(get_llm(), FakeLLMProvider)
        finally:
            llm_mod.AnthropicProvider = orig

    def test_retry_reexecuta_e_depois_relanca(self):
        os.environ["LLM_RETRIES"] = "2"
        llm_mod.time.sleep = lambda *_a, **_k: None  # não dormir no teste
        calls = {"n": 0}

        def _sempre_falha():
            calls["n"] += 1
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            _with_retry(_sempre_falha, label="t")
        self.assertEqual(calls["n"], 3, "deveria tentar 1 original + 2 retries")

    def test_retry_sucede_apos_falha_transiente(self):
        os.environ["LLM_RETRIES"] = "2"
        llm_mod.time.sleep = lambda *_a, **_k: None
        calls = {"n": 0}

        def _falha_uma_vez():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transiente")
            return "ok"

        self.assertEqual(_with_retry(_falha_uma_vez, label="t"), "ok")
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
