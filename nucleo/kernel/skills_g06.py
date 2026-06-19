"""Handlers determinísticos da G06 Dados & Analytics — o cálculo real (não LLM) que
torna a guilda de dados útil ao cliente: curvas de retenção por coorte, score de churn
explicável, forecast com IC + backtest, detecção de anomalia vs. baseline sazonal,
auditoria de drift nas 4 dimensões e suite de qualidade/contrato de dados.

Mesmo padrão de skills_finance/skills_custops: cada handler é puro/determinístico,
sem aleatoriedade e sem datas do sistema; os campos calculados vão no TOP-LEVEL do
output e o grader genérico de contrato valida `expected` direto.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("cohort_retention")
def cohort_retention(state, *, llm, store, spec):
    """g6-cohort-analyst — curvas de retenção D1/D7/D30 sobre o grão canônico.

    Input: state['task']['cohort'] = {size, retained: {d1, d7, d30}, prev_d30_pct?, segment?}.
    Retenção = retidos no dia N / tamanho da coorte. Sinaliza queda anômala de D30
    vs. coorte anterior (drop >= 10pp aciona o churn-predictor)."""
    c = state["task"].get("cohort", {}) or {}
    size = c.get("size", 0) or 0
    ret = c.get("retained", {}) or {}
    def _pct(day):
        v = ret.get(day, 0) or 0
        return round(v / size * 100, 1) if size else 0.0
    d1, d7, d30 = _pct("d1"), _pct("d7"), _pct("d30")
    prev = c.get("prev_d30_pct")
    drop_pp = round(prev - d30, 1) if prev is not None else 0.0
    retention_drop = prev is not None and drop_pp >= 10
    status = "queda" if retention_drop else ("saudavel" if d30 >= 30 else "atencao")
    return _out(spec, state, {
        "cohort_size": size, "segment": c.get("segment"),
        "d1_pct": d1, "d7_pct": d7, "d30_pct": d30,
        "retention_drop": retention_drop, "drop_pp": drop_pp,
        "alert_churn_predictor": retention_drop, "status": status,
        "metric_canonical": True,
    }, f"Voce e {spec['id']}: coorte {size}, D30 {d30}%, status {status}.", llm)


@register("churn_risk_score")
def churn_risk_score(state, *, llm, store, spec):
    """g6-churn-predictor — score de propensão a churn (0..100) por cliente, explicável.

    Input: state['task']['churn'] = {customers: [{id, days_inactive, engagement (0..1),
    activated (bool), support_tickets}], inference_cost?, value_per_retained?}.
    Score determinístico por features ponderadas; explicabilidade = top fatores.
    C3: custo de inferência por score <= 25% do valor capturado pela retenção."""
    ch = state["task"].get("churn", {}) or {}
    customers = ch.get("customers", []) or []
    scored = []
    for cu in customers:
        inactive = cu.get("days_inactive", 0) or 0
        eng = cu.get("engagement", 0) or 0          # 0..1
        activated = bool(cu.get("activated"))
        tickets = cu.get("support_tickets", 0) or 0
        score = 0
        factors = []
        if inactive > 0:
            pts = min(40, inactive * 2)             # 2pts/dia inativo, teto 40
            score += pts
            if pts >= 10:
                factors.append(f"inatividade {inactive}d")
        eng_pts = round((1 - eng) * 30)             # baixo engajamento -> +ate 30
        score += eng_pts
        if eng < 0.4:
            factors.append("baixo engajamento")
        if not activated:
            score += 20
            factors.append("nao ativado")
        if tickets >= 3:
            score += 10
            factors.append(f"{tickets} tickets de suporte")
        score = max(0, min(100, score))
        scored.append({"id": cu.get("id"), "risk_score": score,
                       "risk_band": "alto" if score >= 60 else ("medio" if score >= 30 else "baixo"),
                       "top_factors": factors})
    high_risk = [s for s in scored if s["risk_score"] >= 60]
    avg = round(sum(s["risk_score"] for s in scored) / len(scored), 1) if scored else 0.0
    # C3: firewall econômico
    inf = ch.get("inference_cost", 0) or 0
    value = ch.get("value_per_retained", 0) or 0
    c3_ratio = round(inf / value, 4) if value else 0.0
    c3_ok = c3_ratio <= 0.25
    return _out(spec, state, {
        "scored_count": len(scored), "high_risk_count": len(high_risk),
        "avg_risk_score": avg, "scores": scored,
        "explainable": all(len(s["top_factors"]) > 0 for s in high_risk) if high_risk else True,
        "c3_ratio": c3_ratio, "c3_ok": c3_ok,
    }, f"Voce e {spec['id']}: {len(high_risk)}/{len(scored)} de alto risco, C3 ok={c3_ok}.", llm)


@register("demand_revenue_forecast")
def demand_revenue_forecast(state, *, llm, store, spec):
    """g6-forecaster — previsão de demanda/receita com IC e cenários + backtest (MAPE).

    Input: state['task']['forecast'] = {history: [valores], periods?, z?, backtest: {actual, predicted}}.
    Previsão = média móvel * crescimento médio; IC por desvio-padrão dos resíduos.
    MAPE do backtest = média de |actual-pred|/actual; meta padrão <= 15%."""
    f = state["task"].get("forecast", {}) or {}
    hist = f.get("history", []) or []
    n = len(hist)
    periods = f.get("periods", 1) or 1
    # crescimento médio período-a-período
    if n >= 2:
        rates = [(hist[i] - hist[i - 1]) / hist[i - 1] for i in range(1, n) if hist[i - 1]]
        growth = sum(rates) / len(rates) if rates else 0.0
    else:
        growth = 0.0
    last = hist[-1] if hist else 0
    point = round(last * ((1 + growth) ** periods), 2)
    # IC: amplitude por dispersão histórica (desvio absoluto médio)
    if n >= 2:
        mean = sum(hist) / n
        mad = sum(abs(x - mean) for x in hist) / n
    else:
        mad = 0.0
    z = f.get("z", 1.96)
    margin = round(z * mad, 2)
    ci_low = round(point - margin, 2)
    ci_high = round(point + margin, 2)
    scenarios = {
        "base": point,
        "otimista": round(last * ((1 + growth * 1.5) ** periods), 2),
        "pessimista": round(last * ((1 + growth * 0.5) ** periods), 2),
    }
    # backtest: MAPE
    bt = f.get("backtest", {}) or {}
    actual = bt.get("actual", []) or []
    pred = bt.get("predicted", []) or []
    pairs = [(a, p) for a, p in zip(actual, pred) if a]
    mape = round(sum(abs(a - p) / a for a, p in pairs) / len(pairs) * 100, 1) if pairs else 0.0
    target = f.get("mape_target", 15.0)
    backtest_passed = mape <= target
    return _out(spec, state, {
        "point_forecast": point, "growth_rate": round(growth, 4),
        "ci_low": ci_low, "ci_high": ci_high, "ci_margin": margin,
        "scenarios": scenarios, "mape_pct": mape, "backtest_passed": backtest_passed,
        "has_interval": True,
    }, f"Voce e {spec['id']}: forecast {point} (IC [{ci_low},{ci_high}]), MAPE {mape}%.", llm)


@register("anomaly_score")
def anomaly_score(state, *, llm, store, spec):
    """g6-anomaly-detector — desvio estatístico vs. baseline sazonal + severidade.

    Input: state['task']['series'] = {baseline_mean, baseline_std, value, seasonal_factor?}.
    z = (value - baseline*sazonalidade) / std. |z|>=3 = critico, >=2 = alto, >=1 = medio.
    Anomalia detectada quando |z| >= 2 (banda de confiança ~95%)."""
    s = state["task"].get("series", {}) or {}
    mean = s.get("baseline_mean", 0) or 0
    std = s.get("baseline_std", 0) or 0
    value = s.get("value", 0) or 0
    seasonal = s.get("seasonal_factor", 1.0) or 1.0
    expected = mean * seasonal
    z = round((value - expected) / std, 2) if std else 0.0
    az = abs(z)
    if az >= 3:
        severity = "critico"
    elif az >= 2:
        severity = "alto"
    elif az >= 1:
        severity = "medio"
    else:
        severity = "normal"
    detected = az >= 2
    direction = "queda" if z < 0 else ("pico" if z > 0 else "estavel")
    return _out(spec, state, {
        "z_score": z, "expected_value": round(expected, 2), "observed_value": value,
        "anomaly_detected": detected, "severity": severity, "direction": direction,
        "alert_routed": detected,
    }, f"Voce e {spec['id']}: z={z}, severidade {severity}, detectado={detected}.", llm)


@register("drift_check")
def drift_check(state, *, llm, store, spec):
    """g6-drift-detector — compara telemetria vs. baseline de promoção nas 4 dimensões.

    Input: state['task']['drift'] = {quality_drop_pp, cost_increase_pct, volume_change_pct,
    prompt_hash_changed, economics_recomputed}.
    Thresholds NÚCLEO: quality >=5pp/mês, cost >=15%/mês, volume +-30%/mês,
    prompt = hash mudou sem recálculo de economia. Drift confirmado -> rebaixa modo."""
    d = state["task"].get("drift", {}) or {}
    q_drop = d.get("quality_drop_pp", 0) or 0
    c_inc = d.get("cost_increase_pct", 0) or 0
    v_chg = d.get("volume_change_pct", 0) or 0
    prompt_changed = bool(d.get("prompt_hash_changed"))
    econ_recomputed = bool(d.get("economics_recomputed"))
    dims = {
        "quality": q_drop >= 5,
        "cost": c_inc >= 15,
        "volume": abs(v_chg) >= 30,
        "prompt": prompt_changed and not econ_recomputed,
    }
    drifted = [k for k, v in dims.items() if v]
    drift_confirmed = len(drifted) > 0
    demote_mode = drift_confirmed
    return _out(spec, state, {
        "dimensions": dims, "drifted_dimensions": drifted,
        "drift_confirmed": drift_confirmed, "drift_count": len(drifted),
        "demote_mode": demote_mode, "target_mode": "ASSISTED" if demote_mode else "AUTONOMOUS",
    }, f"Voce e {spec['id']}: {len(drifted)} dimensoes em drift {drifted}, rebaixar={demote_mode}.", llm)


@register("dataquality_suite")
def dataquality_suite(state, *, llm, store, spec):
    """g6-data-quality (GUARDIAN) — suite de testes de completude/duplicata/freshness/
    integridade por dataset; bloqueia load fora de contrato (C6).

    Input: state['task']['dataset'] = {row_count, null_count, duplicate_count,
    freshness_minutes, sla_minutes?, orphan_fk_count, pii_unexpected?}.
    Thresholds: duplicatas > 0 reprova; nulos > 1% reprova; freshness > SLA reprova;
    FK órfã > 0 reprova; PII inesperada reprova (aciona LGPD)."""
    ds = state["task"].get("dataset", {}) or {}
    rows = ds.get("row_count", 0) or 0
    nulls = ds.get("null_count", 0) or 0
    dups = ds.get("duplicate_count", 0) or 0
    freshness = ds.get("freshness_minutes", 0) or 0
    sla = ds.get("sla_minutes", 60) or 60
    orphans = ds.get("orphan_fk_count", 0) or 0
    pii = bool(ds.get("pii_unexpected"))
    null_pct = round(nulls / rows * 100, 2) if rows else 0.0
    dup_pct = round(dups / rows * 100, 2) if rows else 0.0
    checks = {
        "completeness": null_pct <= 1.0,
        "uniqueness": dups == 0,
        "freshness": freshness <= sla,
        "referential_integrity": orphans == 0,
        "privacy_lgpd": not pii,
    }
    failed = [k for k, v in checks.items() if not v]
    suite_passed = len(failed) == 0
    return _out(spec, state, {
        "row_count": rows, "null_pct": null_pct, "duplicate_pct": dup_pct,
        "checks": checks, "failed_checks": failed, "failed_count": len(failed),
        "suite_passed": suite_passed, "contract_certified": suite_passed,
        "block_load": not suite_passed, "trigger_lgpd": pii,
    }, f"Voce e {spec['id']}: {len(failed)} testes reprovados {failed}, passou={suite_passed}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3 — g6-metrics-modeler: validação determinística da definição de métrica.
# ---------------------------------------------------------------------------
_METRIC_REQUIRED = ("name", "formula", "grain", "window", "source")


@register("metric_definition_check")
def metric_definition_check(state, *, llm, store, spec):
    t = state["task"]
    m = t.get("metric", {}) or {}
    existing = (t.get("catalog", {}) or {}).get("metrics", []) or []
    missing = [f for f in _METRIC_REQUIRED if not m.get(f)]
    dup = None
    for e in existing:
        if e.get("name") and e.get("name") == m.get("name"):
            dup = e.get("name"); break
        if e.get("formula") and e.get("formula") == m.get("formula") and m.get("grain") and e.get("grain") == m.get("grain"):
            dup = e.get("name"); break
    valid = (not missing) and dup is None
    status = "accepted" if valid else ("duplicate" if dup else "needs_revision")
    return _out(spec, state, {
        "agent_id": spec["id"], "metric": m.get("name"), "valid": valid,
        "missing_fields": missing, "duplicate_of": dup, "status": status,
        "requires_human_review": not valid,
    }, f"Voce e {spec['id']}: metrica {m.get('name')} valid={valid} status={status}.", llm)

# ---------------------------------------------------------------------------
# Burn-down Track A — g6-experiment-analyst: leitura determinística de A/B.
# ---------------------------------------------------------------------------
@register("experiment_readout")
def experiment_readout(state, *, llm, store, spec):
    """g6-experiment-analyst — recomenda ship/kill/iterate com rigor estatístico.

    Input: state['task']['experiment_readout'] = {
      pre_registered, primary_metric_canonical, peeking_detected, comparisons,
      control_n, control_conversions, treatment_n, treatment_conversions,
      alpha, power_ok, guardrail_delta_pct, guardrail_min_delta_pct
    }
    Usa z-test aproximado de duas proporções; aplica Bonferroni por comparisons.
    """
    import math
    e = state["task"].get("experiment_readout", {}) or {}
    cn = e.get("control_n", 0) or 0
    tn = e.get("treatment_n", 0) or 0
    cc = e.get("control_conversions", 0) or 0
    tc = e.get("treatment_conversions", 0) or 0
    alpha = e.get("alpha", 0.05) or 0.05
    comparisons = max(1, e.get("comparisons", 1) or 1)
    adjusted_alpha = round(alpha / comparisons, 5)
    z_threshold = 2.576 if adjusted_alpha <= 0.01 else (1.96 if adjusted_alpha <= 0.05 else 1.645)
    cr = cc / cn if cn else 0.0
    tr = tc / tn if tn else 0.0
    uplift_pp = round((tr - cr) * 100, 2)
    pooled = (cc + tc) / (cn + tn) if (cn + tn) else 0.0
    se = math.sqrt(pooled * (1 - pooled) * (1 / cn + 1 / tn)) if cn and tn and 0 < pooled < 1 else 0.0
    z_stat = round((tr - cr) / se, 3) if se else 0.0
    significant = abs(z_stat) >= z_threshold
    guardrail_delta = e.get("guardrail_delta_pct", 0) or 0
    guardrail_min = e.get("guardrail_min_delta_pct", -5) if e.get("guardrail_min_delta_pct") is not None else -5
    guardrail_ok = guardrail_delta >= guardrail_min
    pre_registered = bool(e.get("pre_registered"))
    canonical = bool(e.get("primary_metric_canonical", True))
    peeking = bool(e.get("peeking_detected"))
    power_ok = bool(e.get("power_ok", True))
    valid = pre_registered and canonical and not peeking and power_ok and guardrail_ok
    if not valid:
        decision = "iterate"
    elif significant and uplift_pp > 0:
        decision = "ship"
    elif significant and uplift_pp < 0:
        decision = "kill"
    else:
        decision = "iterate"
    return _out(spec, state, {
        "control_rate_pct": round(cr * 100, 2), "treatment_rate_pct": round(tr * 100, 2),
        "uplift_pp": uplift_pp, "z_stat": z_stat, "adjusted_alpha": adjusted_alpha,
        "significant": significant, "guardrail_ok": guardrail_ok, "valid_readout": valid,
        "decision": decision, "learning_registered": valid,
    }, f"Voce e {spec['id']}: uplift {uplift_pp}pp, z={z_stat}, decisao {decision}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3-A final - g6-pipeline-builder: revisao deterministica de run de pipeline.
# Precedencia de bloqueio: contrato quebrado (a montante bloqueia load) > run falhou >
# duplicatas pos-load > reprocesso nao idempotente > schema falhou > freshness violada > ok.
# C2: dados frescos, completos, dentro do contrato (DELIVERED = run_succeeded && contract_passed).
# ---------------------------------------------------------------------------
@register("pipeline_run_review")
def pipeline_run_review(state, *, llm, store, spec):
    r = state["task"].get("run", {}) or {}
    contract_passed = bool(r.get("contract_passed", True))
    run_succeeded = bool(r.get("run_succeeded", True))
    duplicate_count = int(r.get("duplicates", 0) or 0)
    is_reprocess = bool(r.get("is_reprocess", False))
    idempotent = bool(r.get("idempotent_reprocess", True))
    schema_ok = bool(r.get("schema_test_passed", True))
    freshness = float(r.get("freshness_minutes", 0) or 0)
    sla = float(r.get("sla_minutes", 0) or 0)
    fresh = (sla <= 0) or freshness <= sla

    if not contract_passed:
        status = "contrato_quebrado"
    elif not run_succeeded:
        status = "run_falhou"
    elif duplicate_count > 0:
        status = "duplicatas"
    elif is_reprocess and not idempotent:
        status = "reprocesso_nao_idempotente"
    elif not schema_ok:
        status = "schema_falhou"
    elif not fresh:
        status = "freshness_violada"
    else:
        status = "ok"

    load_blocked = status != "ok"
    run_clean = run_succeeded and contract_passed and duplicate_count == 0
    return _out(spec, state, {
        "agent_id": spec["id"], "fresh": fresh, "duplicate_count": duplicate_count,
        "contract_passed": contract_passed, "status": status, "load_blocked": load_blocked,
        "run_clean": run_clean, "requires_human_review": load_blocked,
    }, f"Voce e {spec['id']}: run {status}, load {'bloqueado' if load_blocked else 'ok'}.", llm)


# ---------------------------------------------------------------------------
# Burn-down PR61 — g6-nl2sql: plano determinístico NL→SQL sobre camada semântica.
# ---------------------------------------------------------------------------
_NL2SQL_METRICS = {
    "north_star": {"table": "events", "expr": "SUM(value)", "time_col": "event_date"},
    "revenue": {"table": "invoices", "expr": "SUM(amount)", "time_col": "issued_at"},
    "activation_rate": {"table": "product_events", "expr": "AVG(activated)", "time_col": "event_date"},
    "churn_rate": {"table": "subscriptions", "expr": "AVG(churned)", "time_col": "period_start"},
}
_NL2SQL_PII_FIELDS = {"email", "phone", "cpf", "name"}
_NL2SQL_INJECTION_MARKERS = (
    "ignore previous", "ignore as instrucoes", "ignore as instruções", "drop table",
    "delete from", "password", "secret", "segredo", "admin token", "system prompt",
)


def _nl2sql_has_injection(question):
    q = (question or "").lower()
    return any(marker in q for marker in _NL2SQL_INJECTION_MARKERS)


@register("nl2sql_query_plan")
def nl2sql_query_plan(state, *, llm, store, spec):
    """g6-nl2sql — traduz intenção de negócio em plano SQL auditável e seguro.

    Input: state['task']['query_request'] = {
      question, metric, requested_fields, allowed_fields, role, filters, group_by,
      time_window_days, source_refs, repeated_by_dris
    }

    O handler não executa SQL nem inventa métrica: só emite query quando a métrica existe
    na camada semântica, os campos solicitados estão permitidos e a resposta terá fonte.
    PII fora de escopo e prompt-injection bloqueiam a emissão.
    """
    req = state["task"].get("query_request", {}) or {}
    metric = str(req.get("metric") or "")
    meta = _NL2SQL_METRICS.get(metric)
    question = req.get("question", "") or ""
    requested = set(req.get("requested_fields", []) or [])
    allowed = set(req.get("allowed_fields", []) or [])
    role = req.get("role", "") or ""
    filters = req.get("filters", {}) or {}
    group_by = req.get("group_by")
    days = int(req.get("time_window_days", 30) or 30)
    source_refs = req.get("source_refs", []) or []

    injection_blocked = _nl2sql_has_injection(question)
    forbidden_fields = sorted(requested - allowed)
    pii_requested = sorted(requested & _NL2SQL_PII_FIELDS)
    pii_blocked = bool(pii_requested) and role not in {"privacy_analyst", "legal_privacy"}
    metric_canonical = meta is not None
    source_cited = bool(source_refs)
    access_granted = not forbidden_fields and not pii_blocked

    if injection_blocked:
        status = "blocked_injection"
    elif not metric_canonical:
        status = "needs_metric_mapping"
    elif not access_granted:
        status = "blocked_access"
    elif not source_cited:
        status = "needs_source_citation"
    else:
        status = "ready"

    sql = None
    selected_table = meta["table"] if meta else None
    if status == "ready" and meta is not None:
        select_parts = []
        if group_by:
            select_parts.append(group_by)
        select_parts.append(f"{meta['expr']} AS {metric}")
        where = [f"{meta['time_col']} >= CURRENT_DATE - INTERVAL '{days} days'"]
        for key in sorted(filters):
            where.append(f"{key} = :{key}")
        sql = "SELECT " + ", ".join(select_parts) + f" FROM {selected_table} WHERE " + " AND ".join(where)
        if group_by:
            sql += f" GROUP BY {group_by}"

    sql_ready = status == "ready"
    requires_human_review = status in {"needs_metric_mapping", "needs_source_citation"}
    risk = "high" if status.startswith("blocked") else ("medium" if requires_human_review else "low")
    suggests_dashboard = bool(req.get("repeated_by_dris", 0) and req.get("repeated_by_dris", 0) >= 3)

    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "nl2sql_query_plan",
        "selected_metric": metric, "selected_table": selected_table,
        "metric_canonical": metric_canonical, "source_cited": source_cited,
        "access_granted": access_granted, "pii_blocked": pii_blocked,
        "injection_blocked": injection_blocked, "forbidden_fields": forbidden_fields,
        "sql_ready": sql_ready, "sql": sql, "status": status, "risk": risk,
        "requires_human_review": requires_human_review, "suggests_dashboard": suggests_dashboard,
    }, f"Voce e {spec['id']}: metrica {metric}, status {status}, SQL pronto={sql_ready}.", llm)
