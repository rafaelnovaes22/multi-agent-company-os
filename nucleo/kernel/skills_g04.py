"""Handlers determinísticos da G04 Qualidade & Eval — o cálculo real (não LLM) que
torna a guilda de qualidade útil: medir cobertura, drift vs baseline, SLA sob carga,
pass@k, agreement-rate em SHADOW e a decisão binária do quality-gate. Cada handler é
puro/determinístico: mede números a partir de state["task"] e devolve campos no
top-level do output (o grader genérico de contrato valida `expected` direto).

Mesmo padrão de skills_finance/skills_custops: assinatura
handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
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


def _pct_at(values, q):
    """Percentil determinístico (nearest-rank) sobre uma lista de números."""
    if not values:
        return 0.0
    s = sorted(values)
    rank = max(1, int(round(q / 100.0 * len(s) + 0.5)))
    rank = min(rank, len(s))
    return float(s[rank - 1])


@register("coverage_check")
def coverage_check(state, *, llm, store, spec):
    """g4-test-coverage — mede cobertura por módulo, exige >=80%, isola gaps críticos
    (caminhos de erro/PII) e mede dívida de cobertura vs baseline. Guardian: bloqueia."""
    c = state["task"].get("coverage", {}) or {}
    modules = c.get("modules", []) or []
    threshold = c.get("threshold", 80.0) or 80.0
    total_lines = sum(m.get("lines", 0) or 0 for m in modules)
    covered_lines = sum(m.get("covered", 0) or 0 for m in modules)
    coverage_pct = round(covered_lines / total_lines * 100, 1) if total_lines else 0.0
    # Gaps críticos: módulo marcado critical e descoberto (covered < lines).
    critical_gaps = [
        m.get("name") for m in modules
        if m.get("critical") and (m.get("covered", 0) or 0) < (m.get("lines", 0) or 0)
    ]
    baseline = c.get("baseline_pct")
    coverage_delta = round(coverage_pct - baseline, 1) if baseline is not None else None
    rising_debt = coverage_delta is not None and coverage_delta < 0
    passed = coverage_pct >= threshold and not critical_gaps
    decision = "PASS" if passed else "FAIL"
    return _out(spec, state, {
        "coverage_pct": coverage_pct, "threshold": threshold, "decision": decision,
        "passed": passed, "critical_gaps": critical_gaps, "critical_gap_count": len(critical_gaps),
        "coverage_delta": coverage_delta, "rising_debt": rising_debt,
    }, f"Voce e {spec['id']}: cobertura {coverage_pct}% (min {threshold}%), {len(critical_gaps)} gaps criticos, {decision}.", llm)


@register("regression_drift")
def regression_drift(state, *, llm, store, spec):
    """g4-regression-watcher — delta vs baseline em pass-rate e custo; classifica drift
    (queda >5pp = WARN, custo >1.15x = WARN) e separa regressão real de ruído."""
    r = state["task"].get("regression", {}) or {}
    pass_rate = r.get("pass_rate", 0) or 0
    baseline_pass = r.get("baseline_pass_rate", 0) or 0
    cost = r.get("cost", 0) or 0
    baseline_cost = r.get("baseline_cost", 0) or 0
    delta_pp = round(pass_rate - baseline_pass, 1)
    cost_ratio = round(cost / baseline_cost, 3) if baseline_cost else 1.0
    # Severidade pela magnitude da queda de pass-rate; custo entra como WARN.
    if delta_pp <= -15:
        severity, quality_drift = "P0", True
    elif delta_pp <= -5:
        severity, quality_drift = "P1", True
    else:
        severity, quality_drift = "P2", False
    cost_drift = cost_ratio > 1.15
    drift = "FAIL" if (severity == "P0") else ("WARN" if (quality_drift or cost_drift) else "OK")
    regression_confirmed = quality_drift or cost_drift
    return _out(spec, state, {
        "delta_vs_baseline": delta_pp, "cost_ratio": cost_ratio, "drift": drift,
        "severity": severity, "quality_drift": quality_drift, "cost_drift": cost_drift,
        "regression_confirmed": regression_confirmed,
    }, f"Voce e {spec['id']}: delta {delta_pp}pp vs baseline, custo {cost_ratio}x, drift {drift} ({severity}).", llm)


@register("load_sla")
def load_sla(state, *, llm, store, spec):
    """g4-load-tester — p50/p95/p99, throughput, error-rate; veredito SLA vs targets e
    custo sob carga cruzado com C3 (custo <= 25% do preço para output BL)."""
    l = state["task"].get("load", {}) or {}
    samples = l.get("latencies_ms", []) or []
    requests = l.get("requests", len(samples)) or len(samples)
    errors = l.get("errors", 0) or 0
    duration_s = l.get("duration_s", 1) or 1
    p50 = round(_pct_at(samples, 50), 1)
    p95 = round(_pct_at(samples, 95), 1)
    p99 = round(_pct_at(samples, 99), 1)
    error_rate = round(errors / requests * 100, 2) if requests else 0.0
    throughput = round(requests / duration_s, 2) if duration_s else 0.0
    p95_target = l.get("p95_target_ms", 2000) or 2000
    err_target = l.get("error_rate_target_pct", 1.0)
    sla_ok = p95 <= p95_target and error_rate <= err_target
    # C3: custo por outcome <= 25% do preço para output BL.
    cost = l.get("cost_under_load", 0) or 0
    price = l.get("price")
    c3_ok = True
    cost_ratio = None
    if price:
        cost_ratio = round(cost / price, 4)
        c3_ok = cost_ratio <= 0.25
    sla_verdict = "PASS" if (sla_ok and c3_ok) else "FAIL"
    return _out(spec, state, {
        "p50_ms": p50, "p95_ms": p95, "p99_ms": p99, "throughput_rps": throughput,
        "error_rate_pct": error_rate, "sla_ok": sla_ok, "c3_ok": c3_ok,
        "cost_ratio": cost_ratio, "sla_verdict": sla_verdict,
    }, f"Voce e {spec['id']}: p95 {p95}ms (target {p95_target}), erro {error_rate}%, veredito {sla_verdict}.", llm)


@register("eval_pass_at_k")
def eval_pass_at_k(state, *, llm, store, spec):
    """g4-eval-harness-runner — roda cada case k vezes; pass@k (>=1 sucesso em k) e
    pass-rate por categoria; relatório determinístico e custo médio por case."""
    e = state["task"].get("eval", {}) or {}
    cases = e.get("cases", []) or []
    k = e.get("k", 1) or 1
    n_cases = len(cases)
    # pass@k: case passa se tem >=1 sucesso nos k attempts (successes/attempts informados).
    passed_cases = sum(1 for c in cases if (c.get("successes", 0) or 0) >= 1)
    pass_at_k = round(passed_cases / n_cases * 100, 1) if n_cases else 0.0
    # pass-rate por categoria: successes/attempts agregados por categoria.
    cat_succ, cat_att = {}, {}
    total_cost = 0.0
    for c in cases:
        cat = c.get("category", "geral")
        att = c.get("attempts", k) or k
        cat_succ[cat] = cat_succ.get(cat, 0) + (c.get("successes", 0) or 0)
        cat_att[cat] = cat_att.get(cat, 0) + att
        total_cost += c.get("cost", 0) or 0
    pass_rate_by_category = {
        cat: round(cat_succ[cat] / cat_att[cat] * 100, 1) if cat_att[cat] else 0.0
        for cat in cat_succ
    }
    avg_cost_per_case = round(total_cost / n_cases, 4) if n_cases else 0.0
    return _out(spec, state, {
        "case_count": n_cases, "k": k, "pass_at_k": pass_at_k,
        "pass_rate_by_category": pass_rate_by_category,
        "avg_cost_per_case": avg_cost_per_case,
    }, f"Voce e {spec['id']}: {n_cases} cases, pass@{k} {pass_at_k}%, custo medio {avg_cost_per_case}.", llm)


@register("agreement_rate")
def agreement_rate(state, *, llm, store, spec):
    """g4-shadow-comparator — agreement-rate global e por categoria sobre a amostra de
    SHADOW; exige janela >=14 dias e amostra suficiente; flags de viés; recomendação."""
    s = state["task"].get("shadow", {}) or {}
    pairs = s.get("pairs", []) or []
    window_days = s.get("window_days", 0) or 0
    min_sample = s.get("min_sample", 30) or 30
    sample_size = len(pairs)
    agree = sum(1 for p in pairs if p.get("agent") == p.get("reference"))
    global_rate = round(agree / sample_size * 100, 1) if sample_size else 0.0
    # Por categoria.
    cat_agree, cat_total = {}, {}
    cat_conservative = {}
    for p in pairs:
        cat = p.get("category", "geral")
        cat_total[cat] = cat_total.get(cat, 0) + 1
        if p.get("agent") == p.get("reference"):
            cat_agree[cat] = cat_agree.get(cat, 0) + 1
        elif p.get("agent_more_conservative"):
            cat_conservative[cat] = cat_conservative.get(cat, 0) + 1
    agreement_rate_by_category = {
        cat: round(cat_agree.get(cat, 0) / cat_total[cat] * 100, 1)
        for cat in cat_total
    }
    # Viés sistemático: categoria onde >=60% das discordâncias são do mesmo lado.
    bias_flags = []
    for cat in cat_total:
        disagree = cat_total[cat] - cat_agree.get(cat, 0)
        if disagree and cat_conservative.get(cat, 0) / disagree >= 0.6:
            bias_flags.append(cat)
    threshold = s.get("agreement_threshold", 90.0) or 90.0
    window_ok = window_days >= 14
    sample_ok = sample_size >= min_sample
    weak_categories = [c for c, r in agreement_rate_by_category.items() if r < threshold]
    if window_ok and sample_ok and global_rate >= threshold and not weak_categories:
        recommendation = "promover"
    elif not window_ok or not sample_ok:
        recommendation = "reter_amostra_insuficiente"
    else:
        recommendation = "reter"
    return _out(spec, state, {
        "agreement_rate": global_rate, "agreement_rate_by_category": agreement_rate_by_category,
        "sample_size": sample_size, "shadow_window_days": window_days,
        "window_ok": window_ok, "sample_ok": sample_ok,
        "bias_flags": bias_flags, "weak_categories": weak_categories,
        "recommendation": recommendation,
    }, f"Voce e {spec['id']}: agreement {global_rate}% em {window_days}d ({sample_size} pares), recomendacao {recommendation}.", llm)


@register("quality_gate_decision")
def quality_gate_decision(state, *, llm, store, spec):
    """g4-quality-gate — decisão binária PASS/FAIL determinística: avalia critérios duros
    (pass-rate, cobertura, E2E, regressão, carga) + lovability; bypass auditado. Guardian."""
    g = state["task"].get("gate", {}) or {}
    pass_rate = g.get("pass_rate", 0) or 0
    coverage = g.get("coverage_pct", 0) or 0
    e2e_green = bool(g.get("e2e_green"))
    no_regression = bool(g.get("no_regression"))
    load_pass = bool(g.get("load_pass"))
    lovability = g.get("lovability_score", 0) or 0
    # Thresholds duros explícitos.
    criteria = [
        {"name": "pass_rate", "passed": pass_rate >= 85},
        {"name": "coverage", "passed": coverage >= 80},
        {"name": "e2e", "passed": e2e_green},
        {"name": "no_regression", "passed": no_regression},
        {"name": "load_sla", "passed": load_pass},
        {"name": "lovability", "passed": lovability >= 7},
    ]
    failed = [c["name"] for c in criteria if not c["passed"]]
    bypass = bool(g.get("incident_bypass"))
    technical_pass = not failed
    if technical_pass:
        decision, valid = "PASS", True
    elif bypass:
        decision, valid = "PASS_BYPASS", True   # override de incidente auditado
    else:
        decision, valid = "FAIL", False
    return _out(spec, state, {
        "decision": decision, "valid": valid, "criteria": criteria,
        "failed_criteria": failed, "lovability": lovability,
        "bypass_used": bypass and not technical_pass,
    }, f"Voce e {spec['id']}: gate {decision}, {len(failed)} criterios falhos, lovability {lovability}.", llm)
