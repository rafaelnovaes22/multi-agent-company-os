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

from .execution import get_executor
from .skills import _spec_citations, _tokens, register
from .verification import (
    BROWSER_NECESSARIOS,
    NECESSARIOS,
    STRUCT_NECESSARIOS,
    verify_browser,
    verify_code,
    verify_structure,
)


@register("spec_executor")
def spec_executor(state, *, llm, store, spec):
    """Técnicos verificáveis cujo `delivered` vem de um ORÁCULO, não de auto-declaração.

    Duas naturezas, roteadas pelo oráculo (held-out, autorado no eval-case; o agente nunca o vê):
      code-exec  (F0/F3/F4a): g3-build-error-resolver, g3-backend/frontend-builder, g3-infra-devops.
                 `verify_code` re-deriva os sinais do ARTEFATO {files} + execução real (F2).
      estrutural (F4b):       g3-incident-responder. `oracle["structure"]` define o schema do
                 documento (postmortem); `verify_structure` checa completude/consistência. SEM
                 execução ⇒ delivered_ok sempre False (ASSISTED, garantia parcial honesta).

    Lê de state['task']: artifact, seed, oracle. O veredito vem do oráculo — nunca de um
    booleano de sucesso declarado pelo caso.
    """
    task = state.get("task", {}) or {}
    artifact = task.get("artifact") or {}
    seed = task.get("seed") or {}
    oracle = task.get("oracle") or {}
    artifact_type = task.get("artifact_type") or "build_error_resolver.artifact"
    routed_to = task.get("routed_to") or spec["id"]

    # Roteia pela natureza do oráculo: structure ⇒ verificação estrutural (sem execução);
    # senão code-exec (default InertExecutor offline; a F2 pluga o DockerExecutor sem tocar aqui).
    if oracle.get("browser"):
        v = verify_browser(artifact, oracle)
        signal_keys = BROWSER_NECESSARIOS
    elif oracle.get("structure"):
        v = verify_structure(artifact, oracle)
        signal_keys = STRUCT_NECESSARIOS
    else:
        v = verify_code(artifact, seed, oracle, executor=get_executor())
        signal_keys = NECESSARIOS
    static_ok = v["static_ok"]
    # status honesto: verificado estaticamente vs reprovado (com o 1º critério que falhou).
    status = "verified_static" if static_ok else f"rejected:{v['first_fail']}"
    # delivered nunca é True offline; trabalho não-verificável exige revisão humana.
    requires_review = not static_ok

    rationale = llm.complete(
        f"Voce e {spec['id']}: verificacao OFFLINE do artefato — static_ok={static_ok}, "
        f"first_fail={v['first_fail']}, delivered_ok={v['delivered_ok']} (tests_pass={v['tests_pass']})."
    )

    out = {
        "agent_id": spec["id"],
        "handler_kind": "spec_executor",
        "artifact_type": artifact_type,
        "static_ok": static_ok,
        "tests_pass": v["tests_pass"],  # "UNVERIFIED"/bool (code-exec) | "N/A" (estrutural)
        "delivered_ok": v["delivered_ok"],  # offline/estrutural: SEMPRE False (honesto)
        "first_fail": v["first_fail"],
        "status": status,
        "requires_human_review": requires_review,
        "routed_to": routed_to,
        "rationale": rationale,
        "by": spec["id"],
        "tenant": task.get("tenant_id"),
    }
    # sinais do oráculo (função do artefato) — achatados p/ o grader checar direto (ausente ⇒ False).
    for k in signal_keys:
        out[k] = v["signals"].get(k, False)
    return {
        "output": out,
        "cost_tokens": _tokens(rationale),
        "citations": _spec_citations(state, spec),
    }
