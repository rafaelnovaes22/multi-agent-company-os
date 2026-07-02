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


def _prompt(request: str, seed: dict, attempt: int, feedback: str | None) -> str:
    """Monta o prompt do gerador. SÓ pedido + semente + feedback da execução anterior —
    nada do oráculo (bug_markers/protected/held-out) entra aqui."""
    parts = [
        "Você é um engenheiro de software. Corrija/implemente o pedido abaixo no repositório dado.",
        "Regras: NÃO modifique arquivos de teste; devolva o conteúdo COMPLETO de cada arquivo alterado.",
        'Responda SOMENTE com JSON válido no formato {"files": {"caminho/arquivo": "conteúdo completo"}}.',
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
    test_cmd = oracle.get("test_cmd") or "pytest -q"
    runtime = oracle.get("runtime") or "python"
    can_loop = executor is not None and getattr(executor, "available", False)

    history: list[dict] = []
    artifact_files: dict | None = None
    feedback = None
    loop_green = False

    for attempt in range(1, max_iters + 1):
        text = llm.complete(_prompt(request, seed, attempt, feedback), max_tokens=4096)
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
            # sem executor real não há red→green: one-shot honesto, delivered fica com o caller
            history.append({"attempt": attempt, "parsed": True, "tests_pass": None,
                            "dropped_heldout_paths": dropped, "no_executor": True})
            break
        merged = dict(seed)
        merged.update(files)
        detail = executor.run_tests_detail(merged, test_cmd=test_cmd, runtime=runtime)
        verdict = detail.get("passed")
        history.append({"attempt": attempt, "parsed": True, "tests_pass": verdict,
                        "dropped_heldout_paths": dropped})
        if verdict is True:
            loop_green = True
            break
        if verdict is None:
            break   # erro de infra: iterar às cegas não é sinal, é ruído
        feedback = detail.get("output") or "os testes visíveis falharam (sem saída capturada)"

    return {"artifact": {"files": artifact_files or {}},
            "attempts": len(history), "loop_green": loop_green, "history": history}
