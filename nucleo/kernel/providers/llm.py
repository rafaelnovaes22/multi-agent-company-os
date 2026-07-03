"""Camada de abstração de LLM (C7 — portability over lock-in).

Specs e agentes NUNCA importam um SDK de provider direto. Eles recebem um
`LLMProvider`. Trocar de modelo/fornecedor é configuração, não código de agente.

Default = FakeLLMProvider (offline, determinístico, custo zero) — é o que faz
os agentes nascerem em SHADOW sem precisar de chave de API nem rede.
"""
from __future__ import annotations
import abc
import logging
import os
import time

_log = logging.getLogger(__name__)

# Robustez do provider real (C7). Em produção (PILOT/AUTONOMOUS) uma chamada pendurada
# travaria o nó do grafo, e um erro transiente (5xx/rede) derrubaria a entrega. Ambos são
# configuráveis por env; valem só para os providers REAIS — o FakeLLMProvider é offline.
def _timeout_s() -> float:
    try:
        return float(os.environ.get("LLM_TIMEOUT_S", "60"))
    except ValueError:
        return 60.0


def _retries() -> int:
    try:
        return max(0, int(os.environ.get("LLM_RETRIES", "2")))
    except ValueError:
        return 2


def _with_retry(call, *, label: str):
    """Executa `call()` com retry e backoff exponencial em erros transientes. Re-lança a
    última exceção se todas as tentativas falharem (o caller decide o fallback)."""
    attempts = _retries() + 1
    last = None
    for i in range(attempts):
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 — best-effort; transitório vs permanente é opaco no SDK
            last = exc
            if i + 1 < attempts:
                delay = 0.5 * (2 ** i)
                _log.warning("LLM %s falhou (tentativa %d/%d): %s — retry em %.1fs",
                             label, i + 1, attempts, exc, delay)
                time.sleep(delay)
    raise last


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
        def _call():
            msg = self._client.messages.create(
                model=self.model, max_tokens=kwargs.get("max_tokens", 512),
                messages=[{"role": "user", "content": prompt}],
                timeout=_timeout_s(),
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return _with_retry(_call, label=self.name)


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
        from google.genai import types
        self.model = model
        # timeout em ms no http layer do google-genai (vale para todas as chamadas do client).
        http = types.HttpOptions(timeout=int(_timeout_s() * 1000))
        if _use_vertex():
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            self._client = genai.Client(vertexai=True, project=project, location=location,
                                        http_options=http)
            self.backend = f"vertex:{project}/{location}"
        else:
            key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            self._client = (genai.Client(api_key=key, http_options=http) if key
                            else genai.Client(http_options=http))
            self.backend = "developer-api"

    @property
    def name(self) -> str:
        return f"GoogleProvider/{self.model}/{self.backend}"

    def complete(self, prompt: str, **kwargs) -> str:
        from google.genai import types
        cfg_kwargs = dict(
            max_output_tokens=kwargs.get("max_tokens", 512),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        # temperature=0.0 é opt-in do caller (ex.: gerador red→green, que quer variância
        # mínima entre noites p/ o painel ser comparável); ausente = default do modelo.
        if kwargs.get("temperature") is not None:
            cfg_kwargs["temperature"] = kwargs["temperature"]
        cfg = types.GenerateContentConfig(**cfg_kwargs)

        def _call():
            r = self._client.models.generate_content(model=self.model, contents=prompt, config=cfg)
            return (r.text or "").strip()
        return _with_retry(_call, label=self.name)


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
        except Exception as exc:  # noqa: BLE001
            _log.warning("LLM_PROVIDER=anthropic indisponível (%s); usando FakeLLMProvider "
                         "offline. A frota segue, mas SEM LLM real.", exc)
            return FakeLLMProvider()
    if provider in ("google", "gemini", "vertex"):
        try:
            return GoogleProvider(_google_model(role))
        except Exception as exc:  # noqa: BLE001
            _log.warning("LLM_PROVIDER=%s indisponível (%s); usando FakeLLMProvider offline. "
                         "A frota segue, mas SEM LLM real.", provider, exc)
            return FakeLLMProvider()
    _log.warning("LLM_PROVIDER=%r não reconhecido; usando FakeLLMProvider offline.", provider)
    return FakeLLMProvider()
