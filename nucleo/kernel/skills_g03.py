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


# ---------------------------------------------------------------------------
# Burn-down R3 — g3-feature-flagger: decisão determinística de rollout/kill-switch.
# guard-metrics vs thresholds -> rollback/kill; senão ramp progressivo; detecta flag obsoleta.
# ---------------------------------------------------------------------------
@register("feature_flag_rollout")
def feature_flag_rollout(state, *, llm, store, spec):
    t = state["task"]
    flag = t.get("flag", {}) or {}
    rollout = float(flag.get("rollout_pct", 0) or 0)
    step = float(flag.get("ramp_step_pct", 25) or 25)
    gm = flag.get("guard_metrics", {}) or {}
    th = flag.get("thresholds", {}) or {}
    err = float(gm.get("error_rate", 0) or 0)
    lat = float(gm.get("latency_ms", 0) or 0)
    max_err = float(th.get("max_error_rate", 0.02) or 0.02)
    max_lat = float(th.get("max_latency_ms", 800) or 800)
    err_breach = err > max_err
    lat_breach = lat > max_lat
    guard_breached = err_breach or lat_breach
    severe = err > 2 * max_err
    age = float(flag.get("age_days", 0) or 0)
    last_used = float(flag.get("last_used_days", 0) or 0)
    obsolete = age > 90 and last_used > 30
    if guard_breached:
        decision = "kill" if severe else "rollback"
        rollback_triggered, next_pct, requires_review = True, 0.0, True
    elif rollout >= 100:
        decision, rollback_triggered, next_pct, requires_review = "hold", False, 100.0, False
    else:
        decision, rollback_triggered = "proceed_ramp", False
        next_pct, requires_review = min(100.0, rollout + step), False
    return _out(spec, state, {
        "agent_id": spec["id"], "flag": flag.get("name"), "rollout_pct": rollout,
        "guard_breached": guard_breached, "error_breach": err_breach, "latency_breach": lat_breach,
        "decision": decision, "rollback_triggered": rollback_triggered, "next_rollout_pct": next_pct,
        "obsolete": obsolete, "requires_human_review": requires_review,
    }, f"Voce e {spec['id']}: flag {flag.get('name')} rollout {rollout}% -> {decision}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3 — g3-api-contract: detecção determinística de breaking changes (semver).
# ---------------------------------------------------------------------------
@register("api_contract_diff")
def api_contract_diff(state, *, llm, store, spec):
    t = state["task"]
    api = t.get("api", {}) or {}
    old = {f"{e['path']}|{e.get('method', 'GET')}": e for e in (api.get("old", {}) or {}).get("endpoints", []) or []}
    new = {f"{e['path']}|{e.get('method', 'GET')}": e for e in (api.get("new", {}) or {}).get("endpoints", []) or []}
    breaking, non_breaking = [], []
    for key, oe in old.items():
        if key not in new:
            breaking.append({"endpoint": key, "change": "endpoint_removed"}); continue
        ne = new[key]
        old_req, new_req = set(oe.get("required_params", []) or []), set(ne.get("required_params", []) or [])
        for p in sorted(new_req - old_req):
            breaking.append({"endpoint": key, "change": "required_param_added", "param": p})
        for p in sorted(old_req - new_req):
            non_breaking.append({"endpoint": key, "change": "required_param_removed", "param": p})
        if oe.get("response_type") != ne.get("response_type"):
            breaking.append({"endpoint": key, "change": "response_type_changed"})
    for key in sorted(new.keys() - old.keys()):
        non_breaking.append({"endpoint": key, "change": "endpoint_added"})
    compatible = not breaking
    bump = "major" if breaking else ("minor" if non_breaking else "patch")
    return _out(spec, state, {
        "agent_id": spec["id"], "breaking_count": len(breaking), "non_breaking_count": len(non_breaking),
        "breaking_changes": breaking, "compatible": compatible, "recommended_bump": bump,
        "requires_human_review": not compatible,
    }, f"Voce e {spec['id']}: {len(breaking)} breaking change(s), bump {bump}.", llm)
