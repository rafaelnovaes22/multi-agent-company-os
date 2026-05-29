"""Camada de abstração de LLM (C7 — portability over lock-in).

Specs e agentes NUNCA importam um SDK de provider direto. Eles recebem um
`LLMProvider`. Trocar de modelo/fornecedor é configuração, não código de agente.

Default = FakeLLMProvider (offline, determinístico, custo zero) — é o que faz
os agentes nascerem em SHADOW sem precisar de chave de API nem rede.
"""
from __future__ import annotations
import abc
import os


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def complete(self, prompt: str, **kwargs) -> str: ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class FakeLLMProvider(LLMProvider):
    """Determinístico e offline. Usado em SHADOW/CI: sem custo, sem rede, reprodutível."""

    def __init__(self, model: str = "fake-1"):
        self.model = model

    def complete(self, prompt: str, **kwargs) -> str:
        verd = "VÁLIDA" if "verdict=valid" in prompt else "INVÁLIDA"
        return (f"[{self.name}/{self.model}] Parecer offline: cláusula de outcome {verd}. "
                f"(defina ANTHROPIC_API_KEY para usar um LLM real — C7)")


class AnthropicProvider(LLMProvider):
    """Provider real (opcional). Só é instanciado se ANTHROPIC_API_KEY existir e o SDK estiver instalado."""

    def __init__(self, model: str):
        import anthropic  # import tardio: dependência opcional
        self.model = model
        self._client = anthropic.Anthropic()

    def complete(self, prompt: str, **kwargs) -> str:
        msg = self._client.messages.create(
            model=self.model, max_tokens=kwargs.get("max_tokens", 512),
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


# Tier de modelo por papel (configurável; C7). Supervisores/Guardians = modelo forte.
_ROLE_MODEL = {
    "root": "claude-opus-4-8",
    "supervisor": "claude-opus-4-8",
    "guardian": "claude-opus-4-8",
    "worker": "claude-sonnet-4-6",
}


def get_llm(role: str = "worker") -> LLMProvider:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicProvider(_ROLE_MODEL.get(role, "claude-sonnet-4-6"))
        except Exception:
            pass  # SDK ausente / erro -> cai para o provider offline
    return FakeLLMProvider()
