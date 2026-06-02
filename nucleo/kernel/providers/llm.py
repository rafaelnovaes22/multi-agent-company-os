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
                f"(defina LLM_PROVIDER=anthropic|google|vertex para usar um LLM real — C7)")


class AnthropicProvider(LLMProvider):
    """Provider real (opcional). Só é instanciado se ANTHROPIC_API_KEY existir e o SDK estiver instalado."""

    def __init__(self, model: str):
        import anthropic  # import tardio: dependência opcional
        self.model = model
        self._client = anthropic.Anthropic()

    @property
    def name(self) -> str:
        return f"AnthropicProvider/{self.model}"

    def complete(self, prompt: str, **kwargs) -> str:
        msg = self._client.messages.create(
            model=self.model, max_tokens=kwargs.get("max_tokens", 512),
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def _use_vertex() -> bool:
    return os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("1", "true", "yes")


class GoogleProvider(LLMProvider):
    """Provider real Gemini (opcional). Só é instanciado se houver credencial (API key OU
    config Vertex) e o SDK `google-genai` estiver instalado. Atende o papel "generativo" da
    frota (gemini-2.5-flash por padrão). Dois backends (C7 — a escolha é configuração):

      - Vertex AI (corporativo): GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT
        + GOOGLE_CLOUD_LOCATION (default us-central1). Usa ADC (gcloud auth application-default
        login) ou service account via GOOGLE_APPLICATION_CREDENTIALS.
      - Gemini Developer API: GEMINI_API_KEY / GOOGLE_API_KEY.

    O thinking é desligado (thinking_budget=0) nas completions curtas de rationale — barato/
    rápido e suficiente para o caso de uso."""

    def __init__(self, model: str):
        from google import genai  # import tardio: dependência opcional
        self.model = model
        if _use_vertex():
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            self._client = genai.Client(vertexai=True, project=project, location=location)
            self.backend = f"vertex:{project}/{location}"
        else:
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            self._client = genai.Client(api_key=key) if key else genai.Client()
            self.backend = "developer-api"

    @property
    def name(self) -> str:
        return f"GoogleProvider/{self.model}/{self.backend}"

    def complete(self, prompt: str, **kwargs) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            max_output_tokens=kwargs.get("max_tokens", 512),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        r = self._client.models.generate_content(model=self.model, contents=prompt, config=cfg)
        return (r.text or "").strip()


# Tier de modelo por papel (default; C7). Supervisores/Guardians = modelo forte.
# O usuário parametriza o modelo preferido por env, na ordem de precedência (mais
# específico vence): <PROVIDER>_MODEL_<ROLE> > <PROVIDER>_MODEL > LLM_MODEL > default do papel.
#   ex.: GEMINI_MODEL=gemini-2.5-pro            (todos os papéis do Gemini)
#        GEMINI_MODEL_WORKER=gemini-2.5-flash   (só workers)
#        ANTHROPIC_MODEL=claude-opus-4-8        (todos os papéis do Claude)
#        LLM_MODEL=gemini-2.5-flash             (qualquer provider, override global)
_ROLE_MODEL = {
    "root": "claude-opus-4-8",
    "supervisor": "claude-opus-4-8",
    "guardian": "claude-opus-4-8",
    "worker": "claude-sonnet-4-6",
}

# Gemini: default flash em todos os papéis. Suba supervisor/guardian para gemini-2.5-pro
# via env (GEMINI_MODEL_SUPERVISOR=...) se quiser tiering.
_GOOGLE_ROLE_MODEL = {
    "root": "gemini-2.5-flash",
    "supervisor": "gemini-2.5-flash",
    "guardian": "gemini-2.5-flash",
    "worker": "gemini-2.5-flash",
}


def _pick_model(env_prefix: str, role: str, role_map: dict, fallback: str) -> str:
    """Resolve o modelo preferido pelo usuário por env (mais específico vence)."""
    return (
        os.environ.get(f"{env_prefix}_MODEL_{role.upper()}")   # por provider+papel
        or os.environ.get(f"{env_prefix}_MODEL")               # por provider
        or os.environ.get("LLM_MODEL")                         # global
        or role_map.get(role, fallback)                        # default do papel
    )


def _google_model(role: str) -> str:
    return _pick_model("GEMINI", role, _GOOGLE_ROLE_MODEL, "gemini-2.5-flash")


def _anthropic_model(role: str) -> str:
    return _pick_model("ANTHROPIC", role, _ROLE_MODEL, "claude-sonnet-4-6")


def get_llm(role: str = "worker") -> LLMProvider:
    """Resolve o LLMProvider por papel (C7). Provider real é OPT-IN EXPLÍCITO via
    LLM_PROVIDER — sem ele, a frota usa o provider offline (FakeLLMProvider). Isso mantém
    SHADOW/CI/eval determinísticos, sem rede, sem custo e sem reféns de uma chave perdida
    no ambiente (o gate forge/eval depende dessa reprodutibilidade).

      LLM_PROVIDER=anthropic        -> Claude (ANTHROPIC_API_KEY)
      LLM_PROVIDER=google|gemini    -> Gemini Developer API (GEMINI_API_KEY/GOOGLE_API_KEY)
      LLM_PROVIDER=vertex           -> Gemini via Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=true
                                       + GOOGLE_CLOUD_PROJECT + ADC)
      ausente|fake                  -> FakeLLMProvider (offline, default)

    Qualquer falha de SDK/credencial cai para o offline — a frota nunca quebra por falta
    de LLM real."""
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()

    if provider in ("", "fake"):
        return FakeLLMProvider()
    if provider == "anthropic":
        try:
            return AnthropicProvider(_anthropic_model(role))
        except Exception:
            pass
    if provider in ("google", "gemini", "vertex"):
        try:
            return GoogleProvider(_google_model(role))
        except Exception:
            pass
    return FakeLLMProvider()
