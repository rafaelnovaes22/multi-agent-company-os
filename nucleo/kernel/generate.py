"""Gerador red→green (épico VERIFY-IN-EVAL, fase GERADORA — plano §4.7).

Até aqui o `spec_executor` só VERIFICAVA um artefato baked no eval-case; o
`delivered_eligible_rate` media a qualidade das fixtures, não a capacidade do agente.
Este módulo fecha esse gap: o agente GERA o artefato com LLM real e itera contra o
executor até os testes VISÍVEIS ficarem verdes (ou o budget acabar).

Fronteira de honestidade (inegociável):
  - O HELD-OUT jamais entra no prompt nem na execução do loop. Ele decide `delivered`
    só na verificação final (`verify_code`, que injeta o held-out por cima) — o agente
    nunca vê o critério que o julga.
  - O ORÁCULO (bug_markers/protected_files) também fica fora do prompt: o agente recebe
    o que um dev real receberia (pedido + repo-semente + erro da última execução).
  - Patch em path held-out é DESCARTADO antes do loop (autor != provador) e registrado.
  - Sem executor real não há loop: gera one-shot e devolve honesto (loop_green=False).

Uso: `exec_report --generative` roda os casos ELEGÍVEIS (expected.exec_delivered=True)
sem o artifact baked e publica o `delivered_eligible_rate` GENERATIVO — número separado
do replay de fixtures, nunca somado a ele.
"""
from __future__ import annotations

import json
import os
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_TEST_PATH_RE = re.compile(r"(^|/)(tests?[_/]|test_|__tests__/)|\.(test|spec)\.[a-z]+$|_test\.[a-z]+$")


def _has_visible_tests(seed: dict, runtime: str) -> bool:
    """O loop EXECUTÁVEL só faz sentido se a semente tem teste visível para iterar
    (o held-out é oculto por design). Terraform é exceção: `validate` é feedback
    executável significativo mesmo sem arquivos de teste."""
    if runtime == "terraform":
        return True
    return any(_TEST_PATH_RE.search(path) for path in seed)


def _max_iters() -> int:
    try:
        return max(1, int(os.environ.get("GEN_MAX_ITERS", "4")))
    except ValueError:
        return 4


def _extract_files(text: str):
    """Extrai {"files": {path: content}} da resposta do LLM (JSON puro ou cercado).
    Retorna o dict de files ou None se a resposta não parseia no contrato."""
    if not isinstance(text, str) or not text.strip():
        return None
    candidates = [text.strip()]
    candidates += [m.group(1) for m in _FENCE_RE.finditer(text)]
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (ValueError, TypeError):
            continue
        files = obj.get("files") if isinstance(obj, dict) else None
        if isinstance(files, dict) and files \
                and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
            return files
    return None


def _prompt(request: str, seed: dict, attempt: int, feedback: str | None,
            untouchable: list[str] | None = None) -> str:
    """Monta o prompt do gerador. SÓ pedido + semente + feedback da execução anterior —
    nada do oráculo (bug_markers/held-out) entra aqui. `untouchable` são os paths
    protegidos que EXISTEM na semente (visíveis por definição): nomeá-los é o que um
    ticket real faria, e evita queimar budget em patch que a verificação recusaria."""
    parts = [
        "Você é um engenheiro de software. Corrija/implemente o pedido abaixo no repositório dado.",
        "Regras: NÃO modifique arquivos de teste; devolva o conteúdo COMPLETO de cada arquivo alterado.",
        'Responda SOMENTE com JSON válido no formato {"files": {"caminho/arquivo": "conteúdo completo"}}.',
    ]
    if untouchable:
        parts.append("Arquivos que você NÃO pode incluir/modificar: " + ", ".join(untouchable) + ".")
    parts += [
        "",
        f"## Pedido\n{request}",
        "## Repositório (semente)",
    ]
    for path in sorted(seed):
        parts.append(f"### {path}\n```\n{seed[path]}\n```")
    if feedback:
        parts.append(f"## Resultado da sua tentativa anterior (nº {attempt - 1}) — corrija:\n"
                     f"```\n{feedback}\n```")
    return "\n".join(parts)


def generate_red_green(request: str, seed: dict, oracle: dict, llm, executor,
                       *, max_iters: int = None) -> dict:
    """Gera o artefato {files} iterando LLM×executor até verde nos testes VISÍVEIS.

    Do `oracle` este loop usa APENAS test_cmd/runtime (para executar a semente+patch) e
    os PATHS held-out (para descartar patch neles) — conteúdo held-out nunca é lido aqui.
    Retorna {"artifact", "attempts", "loop_green", "history"} — quem decide `delivered`
    é o verify_code do caller, com o held-out injetado.
    """
    seed = seed or {}
    oracle = oracle or {}
    max_iters = max_iters or _max_iters()
    heldout_paths = set(oracle.get("heldout_files") or {})
    protected_paths = set(oracle.get("protected_files") or {})
    test_cmd = oracle.get("test_cmd") or "pytest -q"
    runtime = oracle.get("runtime") or "python"
    visible_tests = _has_visible_tests(seed, runtime)
    # Loop EXECUTÁVEL exige executor real E teste visível na semente; sem teste visível
    # (held-out é oculto por design) o feedback vem da SONDA ESTÁTICA: só o NOME do
    # critério que falhou (first_fail) — nunca os markers/conteúdo do oráculo.
    can_loop = executor is not None and getattr(executor, "available", False) and visible_tests

    history: list[dict] = []
    artifact_files: dict | None = None
    feedback = None
    loop_green = False

    untouchable = sorted((protected_paths | heldout_paths) & set(seed))
    for attempt in range(1, max_iters + 1):
        text = llm.complete(_prompt(request, seed, attempt, feedback, untouchable), max_tokens=4096)
        files = _extract_files(text)
        if files is None:
            history.append({"attempt": attempt, "parsed": False, "tests_pass": None})
            feedback = ('sua resposta não era JSON válido no contrato '
                        '{"files": {"caminho": "conteúdo"}} — responda apenas o JSON')
            continue
        dropped = sorted(p for p in files if p in heldout_paths)
        for p in dropped:
            files.pop(p)   # autor != provador: o agente não escreve o próprio critério
        artifact_files = files
        if not can_loop:
            if visible_tests:
                # executor indisponível: one-shot honesto, delivered fica com o caller
                history.append({"attempt": attempt, "parsed": True, "tests_pass": None,
                                "dropped_heldout_paths": dropped, "no_executor": True})
                break
            # SONDA ESTÁTICA (semente sem teste visível): itera contra os critérios
            # estáticos do verify_code SEM executar. Vaza só o nome do critério reprovado
            # (o mesmo que o CI publicaria) — jamais bug_markers/held-out. O held-out
            # continua decidindo `delivered` na verificação final do caller.
            from .verification import verify_code
            probe = verify_code({"files": files}, seed, oracle, executor=None)
            history.append({"attempt": attempt, "parsed": True, "tests_pass": None,
                            "dropped_heldout_paths": dropped, "static_probe": True,
                            "static_ok": probe["static_ok"], "first_fail": probe["first_fail"]})
            if probe["static_ok"]:
                break   # estático limpo: sem teste visível não há mais o que iterar
            detail = ""
            if probe["first_fail"] == "protected_unmodified":
                offending = sorted(p for p in files if p in protected_paths)
                detail = f" (você incluiu arquivo protegido: {', '.join(offending)} — remova-o do JSON)"
            feedback = (f"verificação estática reprovou no critério '{probe['first_fail']}'{detail} — "
                        "revise o patch (não altere arquivos protegidos/de teste) e reenvie o JSON")
            continue
        merged = dict(seed)
        merged.update(files)
        # arquivos PROTEGIDOS rodam SEMPRE na versão da semente (mesma disciplina da
        # injeção de held-out no verify_code): green obtido reescrevendo o teste-alvo é
        # green vazio — o loop não pode aceitá-lo nem deixar o agente "testar" a burla.
        touched_protected = sorted(p for p in files
                                   if p in protected_paths and p in seed and files[p] != seed[p])
        for p in protected_paths & seed.keys():
            merged[p] = seed[p]
        detail = executor.run_tests_detail(merged, test_cmd=test_cmd, runtime=runtime)
        verdict = detail.get("passed")
        # green executável NÃO basta: a verificação final também exige o estático (ex.:
        # terraform validate passa com o marcador TODO ainda no arquivo). Sonda estática
        # (sem executar, sem vazar markers) fecha o gap antes de aceitar o green.
        probe = None
        if verdict is True and not touched_protected:
            from .verification import verify_code
            probe = verify_code({"files": files}, seed, oracle, executor=None)
        history.append({"attempt": attempt, "parsed": True, "tests_pass": verdict,
                        "dropped_heldout_paths": dropped,
                        "touched_protected_paths": touched_protected,
                        "static_ok": probe["static_ok"] if probe else None})
        if verdict is True and not touched_protected and probe["static_ok"]:
            loop_green = True
            break
        if verdict is None:
            break   # erro de infra: iterar às cegas não é sinal, é ruído
        if verdict is True and touched_protected:
            # o código passa nos testes da semente, mas o patch reescreve arquivo protegido
            # (teste/contrato) — a verificação final reprovaria; devolve o motivo exato.
            feedback = ("seus arquivos passam nos testes, MAS você modificou arquivo(s) "
                        f"protegido(s) de teste/contrato: {', '.join(touched_protected)}. "
                        "Reenvie o JSON sem incluir esses arquivos (não os altere).")
            continue
        if verdict is True:
            feedback = (f"os testes passam, MAS a verificação estática reprovou no critério "
                        f"'{probe['first_fail']}' — revise o patch e reenvie o JSON")
            continue
        feedback = detail.get("output") or "os testes visíveis falharam (sem saída capturada)"

    return {"artifact": {"files": artifact_files or {}},
            "attempts": len(history), "loop_green": loop_green, "history": history}
