"""Handlers determinísticos da G01 Estratégia & Founder Office.

Dá lógica de cálculo real (não-LLM) aos agentes da guilda que tinham `needs_deterministic`
na spec: o okr-steward (north-star diária + score de KRs) e o scenario-planner
(sensibilidade/tornado sobre as variáveis-chave do sizing). Mesmo padrão de
skills_finance/skills_custops: campos calculados no top-level do output, sem
aleatoriedade e sem datas do sistema; o grader genérico de contrato valida o
`expected` de domínio direto.
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


@register("northstar_daily_value")
def northstar_daily_value(state, *, llm, store, spec):
    """g1-okr-steward — north-star "Daily Active Outcomes" pela fórmula versionada
    e scorecard de KRs com alerta de risco.

    Fórmula da north-star (versionada): DAO = outcomes_delivered * quality_factor,
    onde quality_factor = clamp(referral_propensity_score / 100, 0..1). É o valor
    diário auditável (placeholder até o mercado ser definido).

    Cada KR vira score = clamp(actual/target, 0..1). KR em risco quando o score
    fica abaixo de 0.7 (limiar de atenção); off_track abaixo de 0.4.
    """
    ns = state["task"].get("northstar", {}) or {}
    outcomes = ns.get("outcomes_delivered", 0) or 0
    rps = ns.get("referral_propensity_score", 0) or 0
    quality = max(0.0, min(1.0, rps / 100.0))
    daily_value = round(outcomes * quality, 2)

    okr = state["task"].get("okr", {}) or {}
    krs = okr.get("krs", []) or []
    scored = []
    at_risk = []
    for k in krs:
        target = k.get("target", 0) or 0
        actual = k.get("actual", 0) or 0
        score = round(max(0.0, min(1.0, actual / target)), 3) if target else 0.0
        status = "on_track" if score >= 0.7 else ("at_risk" if score >= 0.4 else "off_track")
        scored.append({"name": k.get("name"), "score": score, "status": status})
        if status != "on_track":
            at_risk.append(k.get("name"))
    n = len(scored)
    attainment = round(sum(s["score"] for s in scored) / n, 3) if n else 0.0
    health = "verde" if attainment >= 0.7 and not at_risk else ("amarelo" if attainment >= 0.4 else "vermelho")
    return _out(spec, state, {
        "daily_value": daily_value, "quality_factor": round(quality, 3),
        "kr_count": n, "attainment": attainment, "at_risk_krs": at_risk,
        "at_risk_count": len(at_risk), "scorecard": scored, "health": health,
    }, f"Voce e {spec['id']}: north-star {daily_value}, attainment {attainment}, saude {health}.", llm)


@register("scenario_sensitivity")
def scenario_sensitivity(state, *, llm, store, spec):
    """g1-scenario-planner — sensibilidade/tornado sobre as variáveis-chave do sizing
    e cenários base/upside/downside + trip-wires.

    Resultado base = produto das variáveis (base_value). Para cada variável aplica-se
    o swing (±delta_pct) e mede-se o impacto absoluto no resultado, que ranqueia o
    tornado. Cenários: upside = todas as variáveis no topo do swing; downside = no
    fundo; base = nominal. Trip-wire por variável = limiar nominal*(1-delta_pct)
    (cruzar isso para baixo dispara replanejamento).
    """
    s = state["task"].get("sizing", {}) or {}
    variables = s.get("variables", []) or []

    raw_base = 1.0
    for v in variables:
        raw_base *= (v.get("value", 0) or 0)
    base_value = round(raw_base, 2)

    drivers = []
    tripwires = []
    for v in variables:
        name = v.get("name")
        val = v.get("value", 0) or 0
        delta = v.get("delta_pct", 0) or 0
        # impacto = variação absoluta do resultado quando ESTA variável vai ao topo do swing
        if val:
            high_value = base_value * (1 + delta)
            impact = round(abs(high_value - base_value), 2)
        else:
            impact = 0.0
        drivers.append({"name": name, "impact": impact})
        tripwires.append({"name": name, "threshold": round(val * (1 - delta), 4), "metric": name})
    drivers.sort(key=lambda d: -d["impact"])
    top_driver = drivers[0]["name"] if drivers else None

    # cenários: todas as variáveis movem juntas pelo seu swing
    up = 1.0
    down = 1.0
    for v in variables:
        val = v.get("value", 0) or 0
        delta = v.get("delta_pct", 0) or 0
        up *= val * (1 + delta)
        down *= val * (1 - delta)
    scenarios = {
        "base": base_value,
        "upside": round(up, 2),
        "downside": round(down, 2),
    }
    # spread calculado nos valores CRUS: arredondar endpoint antes da divisão distorce a
    # conta (sp-03: 0.375/0.225 arredondados davam 53.3% em vez de 50.0% — auditoria
    # 2026-07-03). Arredondamento é apresentação, nunca insumo de cálculo.
    spread_pct = round((up - down) / raw_base * 100, 1) if raw_base else 0.0
    return _out(spec, state, {
        "base_value": base_value, "driver_count": len(drivers), "top_driver": top_driver,
        "drivers": drivers, "scenarios": scenarios, "spread_pct": spread_pct,
        "tripwires": tripwires, "tripwire_count": len(tripwires),
    }, f"Voce e {spec['id']}: base {base_value}, top driver '{top_driver}', spread {spread_pct}%.", llm)
