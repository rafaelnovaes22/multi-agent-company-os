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
import shutil
import subprocess
import tempfile

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
    def run_tests(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = 60.0
    ):
        """Aplica `files` a um workspace efêmero e roda `test_cmd`. Retorna:
        True (exit 0) / False (exit != 0) / None (não executou). `runtime` seleciona o
        ambiente de execução ("python" = pytest, "node" = vitest — build do frontend,
        "terraform" = terraform test — natureza ops/dry-run); cada runtime tem sua imagem
        hardened. Implementações REAIS (F2) devem isolar o
        workspace, dropar rede/caps e NUNCA expor segredos do host."""
        ...

    def run_tests_detail(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = 60.0
    ) -> dict:
        """Como `run_tests`, mas com diagnóstico p/ o loop red→green do gerador:
        {"passed": True|False|None, "output": cauda do stdout/stderr}. Default honesto:
        só o veredito, sem saída (implementações reais sobrescrevem p/ dar o erro ao LLM)."""
        return {
            "passed": self.run_tests(
                files, test_cmd=test_cmd, runtime=runtime, timeout_s=timeout_s
            ),
            "output": "",
        }

    @property
    def name(self) -> str:
        return self.__class__.__name__


class InertExecutor(ExecutionProvider):
    """Default. Não executa: toda verificação é UNVERIFIED (None). Honesto offline/F1."""

    @property
    def available(self) -> bool:
        return False

    def run_tests(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = 60.0
    ):
        return None


# ---------------------------------------------------------------------------
# DockerExecutor (F2) — execução real em contêiner HARDENED. O eval-case é canal
# NÃO-CONFIÁVEL: paths são sanitizados; o container roda sem rede, sem capabilities,
# read-only, non-root, com limites e timeout; nenhum segredo do host é exposto.
# ---------------------------------------------------------------------------
def _safe_files(files: dict):
    """Sanitiza o mapa {path: content} do artefato (canal não-confiável). Rejeita paths
    absolutos, com '..' ou drive/backslash — evita escapar do workspace efêmero. Retorna o
    mapa normalizado ou None se algo for inseguro."""
    if not isinstance(files, dict) or not files:
        return None
    safe = {}
    for path, content in files.items():
        if not isinstance(path, str) or not isinstance(content, str):
            return None
        p = path.replace("\\", "/").strip()
        if not p or p.startswith("/") or ".." in p.split("/") or ":" in p:
            return None
        safe[p] = content
    return safe


# Tetos de RECURSO por runtime (anti-DoS: fork-bomb/OOM/loop) — NÃO são a fronteira de
# segurança (essa é network none + cap-drop + no-new-privileges + read-only + non-root, igual
# p/ todos). vitest+esbuild criam muitas threads/processos (pthread_create EAGAIN sob limites de
# pytest), então o runtime node recebe teto maior; o python segue enxuto.
_RESOURCE_LIMITS = {
    "python": {"pids": "256", "memory": "512m", "cpus": "1", "tmpfs": "64m"},
    "node": {"pids": "1024", "memory": "1g", "cpus": "2", "tmpfs": "256m"},
    # terraform (natureza ops/dry-run, F4a): validate/test (command=plan), SEM providers de
    # cloud ⇒ sem rede, determinístico. Escreve .terraform/ em /work e usa /tmp como HOME.
    "terraform": {"pids": "512", "memory": "1g", "cpus": "2", "tmpfs": "256m"},
}


def _uid_gid():
    """uid:gid do processo p/ rodar o container non-root casando o dono do volume (Linux).
    None no Windows (DockerExecutor só roda de fato no runner Linux)."""
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if getuid is None or getgid is None:
        return None
    return f"{getuid()}:{getgid()}"


class DockerExecutor(ExecutionProvider):
    """Executa `test_cmd` sobre o repo (semente+patch) num contêiner descartável e hardened.

    Sandbox (defesa em profundidade; Docker ≠ sandbox por si só):
      --network none   sem rede (o artefato não exfiltra nem baixa nada)
      --cap-drop ALL + --security-opt no-new-privileges   sem capabilities/escalada
      --read-only + --tmpfs /tmp   rootfs imutável; só /work (volume) e /tmp são graváveis
      --user uid:gid   non-root, casando o dono do workspace
      --pids-limit/--memory/--cpus + timeout   contém fork-bomb/OOM/loop infinito
    Cada `runtime` tem sua imagem hardened, já com o runner embutido (sem rede ⇒ nada é
    instalado em runtime):
      python    (EXEC_IMAGE,           default nucleo-exec:latest)           -> pytest
      node      (EXEC_IMAGE_NODE,      default nucleo-exec-node:latest)      -> vitest (frontend)
      terraform (EXEC_IMAGE_TERRAFORM, default nucleo-exec-terraform:latest) -> terraform test (ops/dry-run)
    Erro de infra ⇒ None (UNVERIFIED), nunca um falso verde."""

    def __init__(self, image: str = None, timeout_s: float = 60.0):
        self._images = {
            "python": image or os.environ.get("EXEC_IMAGE", "nucleo-exec:latest"),
            "node": os.environ.get("EXEC_IMAGE_NODE", "nucleo-exec-node:latest"),
            "terraform": os.environ.get("EXEC_IMAGE_TERRAFORM", "nucleo-exec-terraform:latest"),
        }
        self._timeout = timeout_s
        self._avail = None

    def _image_for(self, runtime: str) -> str:
        return self._images.get(runtime or "python", self._images["python"])

    @property
    def name(self) -> str:
        return f"DockerExecutor/{self._images['python']}"

    @property
    def available(self) -> bool:
        if self._avail is None:
            self._avail = self._probe()
        return self._avail

    def _probe(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            r = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                timeout=10,
            )
            return r.returncode == 0
        except Exception:  # noqa: BLE001
            return False

    def run_tests(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = None
    ):
        return self._execute(files, test_cmd=test_cmd, runtime=runtime, timeout_s=timeout_s)[0]

    def run_tests_detail(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = None
    ) -> dict:
        verdict, output = self._execute(
            files, test_cmd=test_cmd, runtime=runtime, timeout_s=timeout_s
        )
        return {"passed": verdict, "output": output}

    def _execute(
        self, files: dict, *, test_cmd: str, runtime: str = "python", timeout_s: float = None
    ):
        if not self.available:
            return None, ""
        safe = _safe_files(files)
        if safe is None:
            _log.warning("DockerExecutor: artefato com paths inseguros — não executa.")
            return None, ""
        image = self._image_for(runtime)
        lim = _RESOURCE_LIMITS.get(runtime or "python", _RESOURCE_LIMITS["python"])
        timeout_s = timeout_s or self._timeout
        with tempfile.TemporaryDirectory(prefix="nucleo-exec-") as wd:
            for path, content in safe.items():
                fp = os.path.join(wd, *path.split("/"))
                os.makedirs(os.path.dirname(fp) or wd, exist_ok=True)
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(content)
            cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                lim["pids"],
                "--memory",
                lim["memory"],
                "--cpus",
                lim["cpus"],
                "--read-only",
                "--tmpfs",
                f"/tmp:rw,size={lim['tmpfs']}",
                "-v",
                f"{wd}:/work:rw",
                "-w",
                "/work",
            ]
            ug = _uid_gid()
            if ug:
                cmd += ["--user", ug]
            cmd += [image, "sh", "-c", test_cmd]
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=timeout_s + 20)
            except subprocess.TimeoutExpired:
                _log.warning("DockerExecutor: timeout em %ss — trata como FALHA.", timeout_s)
                return False, f"timeout: testes excederam {timeout_s}s"
            except Exception as exc:  # noqa: BLE001
                _log.warning("DockerExecutor: erro de infra: %s", exc)
                return None, ""
            # cauda de stdout+stderr p/ o feedback do loop red→green (limitada: o LLM só
            # precisa do erro, não do log inteiro; e a saída é canal não-confiável).
            out = r.stdout if isinstance(r.stdout, bytes) else b""
            err = r.stderr if isinstance(r.stderr, bytes) else b""
            tail = (out + b"\n" + err).decode("utf-8", "replace")[-2000:]
            if r.returncode == 0:
                return True, tail
            # 125 (docker run), 126/127 (exec/cmd não encontrado) = erro de infra, não de teste.
            if r.returncode in (125, 126, 127):
                _log.warning(
                    "DockerExecutor: erro de container (rc=%s): %s",
                    r.returncode,
                    (r.stderr or b"").decode("utf-8", "replace")[:200],
                )
                return None, ""
            return False, tail


def get_executor() -> ExecutionProvider:
    """Resolve o ExecutionProvider por env (EXEC_PROVIDER). Execução real é OPT-IN EXPLÍCITO;
    sem ela (ou se o runner não estiver disponível) cai no InertExecutor — o eval/CI seguem
    offline e nenhuma entrega é creditada como `delivered` sem execução real.

      EXEC_PROVIDER ausente|inert|none -> InertExecutor (default)
      EXEC_PROVIDER=docker             -> DockerExecutor (F2); se o daemon não responde, o
                                          próprio executor reporta available=False ⇒ UNVERIFIED
    """
    provider = os.environ.get("EXEC_PROVIDER", "").strip().lower()
    if provider in ("", "inert", "none", "fake"):
        return InertExecutor()
    if provider == "docker":
        return DockerExecutor()
    _log.warning("EXEC_PROVIDER=%r não reconhecido; usando InertExecutor.", provider)
    return InertExecutor()
