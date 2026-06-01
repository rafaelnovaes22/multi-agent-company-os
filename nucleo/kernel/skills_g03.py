"""Handlers determinísticos da G03 Engenharia — o cálculo real (não LLM) que dá
lógica de domínio aos agentes da Software Factory que a spec marcou como
`needs_deterministic`. Mesmo padrão de skills_finance/skills_custops: campos no
top-level do output; o grader genérico de contrato valida `expected` direto.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations


def _out(spec, state, fields, rationale_prompt, llm):
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("perf_benchmark_delta")
def perf_benchmark_delta(state, *, llm, store, spec):
    """g3-perf-optimizer — compara métrica antes/depois (p95, throughput, custo) de
    forma determinística e só declara melhoria com evidência de benchmark E correção
    preservada (testes verdes). Sem otimização "no escuro" e sem ganho às custas de
    resultado incorreto (KPIs: melhoria p95/p99, redução de custo, regressões=0).

    Inputs em state['task']['benchmark']:
      before, after          — latência p95 (ms) antes/depois (menor é melhor)
      cost_before, cost_after — custo por operação (menor é melhor; opcional)
      tests_passed           — bool: correção preservada (testes verdes)
      slo_registered         — bool: SLO registrado para travar regressão futura
      profiled               — bool: otimização justificada por profiling (não no escuro)
    """
    b = state["task"].get("benchmark", {}) or {}
    before = b.get("before", 0) or 0
    after = b.get("after", 0) or 0
    cost_before = b.get("cost_before")
    cost_after = b.get("cost_after")
    tests_passed = bool(b.get("tests_passed", False))
    slo_registered = bool(b.get("slo_registered", False))
    profiled = bool(b.get("profiled", False))

    # Delta de latência: positivo = melhora (queda de p95).
    latency_delta_pct = round((before - after) / before * 100, 1) if before else 0.0
    cost_delta_pct = (round((cost_before - cost_after) / cost_before * 100, 1)
                      if cost_before else None)

    # Melhoria real exige: ganho de latência > 0, profiling que justifique e correção preservada.
    improved = latency_delta_pct > 0 and profiled and tests_passed
    correctness_preserved = tests_passed
    # DELIVERED só com benchmark melhorado, correção preservada e SLO travando regressão.
    delivered = improved and correctness_preserved and slo_registered

    if not profiled:
        status = "no_escuro"          # otimização sem profiling — rejeitada
    elif not tests_passed:
        status = "regressao"          # ganho às custas de correção — rejeitada
    elif latency_delta_pct <= 0:
        status = "sem_ganho"          # não melhorou (ou regrediu) a métrica-alvo
    elif not slo_registered:
        status = "melhorou_sem_slo"   # melhorou mas falta SLO p/ travar regressão
    else:
        status = "melhorou"

    return _out(spec, state, {
        "latency_delta_pct": latency_delta_pct,
        "cost_delta_pct": cost_delta_pct,
        "improved": improved,
        "correctness_preserved": correctness_preserved,
        "delivered": delivered,
        "status": status,
    }, f"Voce e {spec['id']}: p95 {before}->{after} ({latency_delta_pct}%), status {status}.", llm)
