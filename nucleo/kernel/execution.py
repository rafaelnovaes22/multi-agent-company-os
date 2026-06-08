"""Camada de abstração de EXECUÇÃO (épico VERIFY-IN-EVAL, F1) — a seam que a F2 plugará.

Análoga ao LLMProvider (C7): `verify_code` e o handler `spec_executor` NUNCA falam com um
runner concreto; recebem um `ExecutionProvider`. Trocar "não executa" (F1) por "executa em
contêiner" (F2) é configuração, não código de agente.

Default = InertExecutor: NÃO executa nada e devolve `None` (UNVERIFIED). Mantém o caminho
de eval/CI offline, determinístico e sem rede — e, crucialmente, HONESTO: sem execução real,
`tests_pass` é UNVERIFIED ⇒ `delivered_ok` nunca pode ser True. A F2 adiciona um DockerExecutor
real (runner Linux+Docker), com sandbox defensivo; até lá, opt-in via EXEC_PROVIDER cai no inerte.

Regra de ouro (anti verde-por-fixture): `tests_pass` SÓ pode ser True vindo de uma EXECUÇÃO
real do artefato — jamais de um booleano que o eval-case declara. O eval-case fornece o
COMANDO/critério (test_cmd), nunca o veredito.
"""
from __future__ import annotations
import abc
import logging
import os

_log = logging.getLogger(__name__)

# Resultado de uma verificação por execução:
#   True/False — executou e os testes passaram/falharam (só F2)
#   None       — NÃO executou (UNVERIFIED) — único resultado possível offline/F1
ExecResult = "bool | None"


class ExecutionProvider(abc.ABC):
    @property
    def available(self) -> bool:
        """Se False, o caller trata como UNVERIFIED (não executou)."""
        return False

    @abc.abstractmethod
    def run_tests(self, files: dict, *, test_cmd: str, timeout_s: float = 60.0):
        """Aplica `files` a um workspace efêmero e roda `test_cmd`. Retorna:
        True (exit 0) / False (exit != 0) / None (não executou). Implementações REAIS
        (F2) devem isolar o workspace, dropar rede/caps e NUNCA expor segredos do host."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class InertExecutor(ExecutionProvider):
    """Default. Não executa: toda verificação é UNVERIFIED (None). Honesto offline/F1."""

    @property
    def available(self) -> bool:
        return False

    def run_tests(self, files: dict, *, test_cmd: str, timeout_s: float = 60.0):
        return None


def get_executor() -> ExecutionProvider:
    """Resolve o ExecutionProvider por env (EXEC_PROVIDER). Execução real é OPT-IN EXPLÍCITO;
    sem ela (ou se o runner não estiver disponível) cai no InertExecutor — o eval/CI seguem
    offline e nenhuma entrega é creditada como `delivered` sem execução real.

      EXEC_PROVIDER ausente|inert|none -> InertExecutor (default, F1)
      EXEC_PROVIDER=docker             -> DockerExecutor (F2 — ainda não disponível; cai no inerte)
    """
    provider = os.environ.get("EXEC_PROVIDER", "").strip().lower()
    if provider in ("", "inert", "none", "fake"):
        return InertExecutor()
    if provider == "docker":
        # F2: runner Linux+Docker com sandbox. Enquanto não existe, degrada para inerte
        # com aviso — nunca finge execução.
        _log.warning("EXEC_PROVIDER=docker pedido, mas o DockerExecutor (F2) ainda não está "
                     "disponível; usando InertExecutor (delivered permanece não-verificável).")
        return InertExecutor()
    _log.warning("EXEC_PROVIDER=%r não reconhecido; usando InertExecutor.", provider)
    return InertExecutor()
