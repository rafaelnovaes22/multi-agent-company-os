"""Handlers determinísticos da G00."""
from __future__ import annotations
from .skills import register, _tokens, _spec_citations


def _out(spec, state, fields, rationale_prompt, llm):
    rationale = llm.complete(rationale_prompt)
    out = dict(fields); out["rationale"] = rationale; out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("brain_reconcile_outcomes_traces")
def brain_reconcile_outcomes_traces(state, *, llm, store, spec):
    """brain-indexer (G00): reconcilia outcomes↔traces e enforce de C6.

    KPI central: desvio outcomes↔traces ≤ 1% (FAIL acima disso) e cobertura de
    artefatos (% de runs que terminaram com artefato indexado). Toda run sem
    artefato é não-contável (C6: "sem artefato, a execução não conta").

    Inputs (state["task"]["reconcile"]):
      - outcomes: int — outcomes contabilizados (delivered_event registrados)
      - traces:   int — traces de telemetria observados no período
      - runs: [{"trace_id","artifact"(bool/None),"schema_valid"(bool)}] — runs do período

    Determinístico: desvio = |outcomes-traces|/traces*100 (arredondado 4 casas
    no fator, 2 no pct); FAIL quando desvio > 1.0%. Cobertura = runs com
    artefato / total. Schema enforce: conta runs com artefato porém schema inválido.
    """
    r = state["task"].get("reconcile", {}) or {}
    outcomes = r.get("outcomes", 0) or 0
    traces = r.get("traces", 0) or 0
    runs = r.get("runs", []) or []

    # Desvio outcomes↔traces (base = traces observados; sem traces => sem desvio).
    deviation_pct = round(abs(outcomes - traces) / traces * 100, 2) if traces else 0.0
    threshold = 1.0
    reconciled = deviation_pct <= threshold
    status = "pass" if reconciled else "fail"

    # Enforce C6: runs sem artefato são não-contáveis; cobertura = com artefato / total.
    total_runs = len(runs)
    with_artifact = sum(1 for x in runs if x.get("artifact"))
    uncountable = total_runs - with_artifact  # runs sem artefato (enforce C6)
    coverage_pct = round(with_artifact / total_runs * 100, 1) if total_runs else 100.0

    # Schema enforce: artefato presente mas schema inválido => não conta como válido.
    schema_invalid = sum(1 for x in runs if x.get("artifact") and not x.get("schema_valid", True))
    schema_valid = schema_invalid == 0

    # Run é DELIVERED quando reconciliado E sem run não-contável E schema 100% válido.
    delivered = reconciled and uncountable == 0 and schema_valid

    return _out(spec, state, {
        "deviation_pct": deviation_pct,
        "threshold_pct": threshold,
        "reconciled": reconciled,
        "status": status,
        "total_runs": total_runs,
        "uncountable_runs": uncountable,
        "coverage_pct": coverage_pct,
        "schema_invalid_count": schema_invalid,
        "schema_valid": schema_valid,
        "delivered": delivered,
    }, f"Voce e {spec['id']}: desvio {deviation_pct}% (limite {threshold}%) -> {status}, "
       f"cobertura {coverage_pct}%, {uncountable} runs nao-contaveis.", llm)
