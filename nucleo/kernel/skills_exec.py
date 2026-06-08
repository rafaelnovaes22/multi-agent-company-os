"""Handler `spec_executor` — agentes técnicos cujo `delivered` depende de um ORÁCULO de
verificação, não de auto-declaração (épico VERIFY-IN-EVAL, F0).

Substitui o handler de catálogo genérico (`spec_driven`, que só ecoa o contrato e era dado
como 30/30 verde enquanto o juiz gpt-5 reprovava por "blueprint, não código"). Aqui o agente
entrega um ARTEFATO estruturado `{files:{path:content}}` e o oráculo `verify_code` (held-out,
do eval-case) decide os sinais por inspeção estática do artefato.

OFFLINE (F0, hoje): computa `static_ok` (necessários estáticos) — já reprova lixo/burla e o
adversarial "deleta o teste-alvo". `delivered_ok` é SEMPRE False offline (tests_pass=UNVERIFIED),
porque sem executar não se afirma correção. F2 (runner Linux+Docker) adiciona a execução real.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations
from .verification import verify_code
from .execution import get_executor


@register("spec_executor")
def spec_executor(state, *, llm, store, spec):
    """g3-build-error-resolver (piloto F0) e demais técnicos verificáveis.

    Lê de state['task']:
      artifact — {"files": {path: content}} produzido pelo agente (o patch).
      seed     — {path: content} repo-semente (build vermelho por construção).
      oracle   — {bug_file, protected_files{path: sha}, bug_markers{must_remove, must_contain}}.

    O oráculo é HELD-OUT (autorado no eval-case); o agente nunca o vê. `verify_code` re-deriva
    o veredito do ARTEFATO — nunca lê um booleano de sucesso declarado pelo caso.
    """
    task = state.get("task", {}) or {}
    artifact = task.get("artifact") or {}
    seed = task.get("seed") or {}
    oracle = task.get("oracle") or {}
    artifact_type = task.get("artifact_type") or "build_error_resolver.artifact"
    routed_to = task.get("routed_to") or spec["id"]

    # Executor por env (EXEC_PROVIDER): default InertExecutor ⇒ não executa, tests_pass=UNVERIFIED.
    # A F2 pluga o DockerExecutor real sem tocar este handler nem o eval-case.
    v = verify_code(artifact, seed, oracle, executor=get_executor())
    static_ok = v["static_ok"]
    # status honesto: verificado estaticamente vs reprovado (com o 1º critério que falhou).
    status = "verified_static" if static_ok else f"rejected:{v['first_fail']}"
    # delivered nunca é True offline; trabalho não-verificável exige revisão humana.
    requires_review = not static_ok

    rationale = llm.complete(
        f"Voce e {spec['id']}: verificacao OFFLINE do artefato — static_ok={static_ok}, "
        f"first_fail={v['first_fail']}, delivered_ok={v['delivered_ok']} (tests_pass={v['tests_pass']}).")

    out = {
        "agent_id": spec["id"],
        "handler_kind": "spec_executor",
        "artifact_type": artifact_type,
        # sinais do oráculo (função do artefato) — achatados p/ o grader checar direto:
        "artifact_parseable": v["signals"].get("artifact_parseable", False),
        "touches_bug_file": v["signals"].get("touches_bug_file", False),
        "bug_addressed": v["signals"].get("bug_addressed", False),
        "protected_unmodified": v["signals"].get("protected_unmodified", False),
        "result_parses": v["signals"].get("result_parses", False),
        "no_test_gaming": v["signals"].get("no_test_gaming", False),
        "static_ok": static_ok,
        "tests_pass": v["tests_pass"],       # "UNVERIFIED" offline (F0); bool só em F2
        "delivered_ok": v["delivered_ok"],   # SEMPRE False offline (honesto)
        "first_fail": v["first_fail"],
        "status": status,
        "requires_human_review": requires_review,
        "routed_to": routed_to,
        "rationale": rationale,
        "by": spec["id"],
        "tenant": task.get("tenant_id"),
    }
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}
