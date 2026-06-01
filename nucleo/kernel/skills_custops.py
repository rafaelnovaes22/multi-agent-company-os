"""Handlers determinísticos da G09 Customer Operations — o cálculo real de satisfação,
cumprimento de SLA, deflection, ativação, reembolso, sentimento e priorização de VoC.
Mesmo padrão de skills_finance: campos no top-level do output, grader genérico valida.
"""
from __future__ import annotations

from .skills import register
from .skills_finance import _out   # helper comum (rationale + by + tenant + citations)


@register("csat_nps_score")
def csat_nps_score(state, *, llm, store, spec):
    """g9-csat-analyst — CSAT (% de notas >=4 em 1..5) e detratores; alerta de queda."""
    c = state["task"].get("csat", {}) or {}
    responses = [r.get("score", 0) for r in (c.get("responses", []) or [])]
    n = len(responses)
    csat = round(sum(1 for s in responses if s >= 4) / n * 100, 1) if n else 0.0
    detractors = sum(1 for s in responses if s <= 2)
    prev = c.get("prev_csat_pct")
    drop = prev is not None and csat < prev - 5
    status = "queda" if drop else ("ok" if csat >= 70 else "atencao")
    return _out(spec, state, {
        "csat_pct": csat, "detractor_count": detractors, "responses": n, "status": status,
    }, f"Voce e {spec['id']}: CSAT {csat}% ({n} respostas), {detractors} detratores.", llm)


@register("fulfillment_sla")
def fulfillment_sla(state, *, llm, store, spec):
    """g9-fulfillment-tracker — % de entregas no prazo e desvios (status por transação)."""
    f = state["task"].get("fulfillment", {}) or {}
    txns = f.get("transactions", []) or []
    on_time = sum(1 for t in txns if t.get("status") == "entregue_no_prazo")
    late = sum(1 for t in txns if t.get("status") == "atrasado")
    pending = sum(1 for t in txns if t.get("status") == "pendente")
    delivered = on_time + late
    sla = round(on_time / delivered * 100, 1) if delivered else 100.0
    return _out(spec, state, {
        "total": len(txns), "on_time_count": on_time, "late_count": late,
        "pending_count": pending, "sla_pct": sla, "delivered_outcomes": delivered,
    }, f"Voce e {spec['id']}: SLA {sla}% ({on_time}/{delivered} no prazo), {late} atrasadas.", llm)


@register("kb_deflection")
def kb_deflection(state, *, llm, store, spec):
    """g9-kb-curator — deflection (tickets cobertos por artigo / total) e lacunas de cobertura."""
    k = state["task"].get("kb", {}) or {}
    themes = k.get("themes", []) or []
    total = sum(t.get("tickets", 0) for t in themes)
    deflected = sum(t.get("tickets", 0) for t in themes if t.get("has_article"))
    gaps = [t.get("theme") for t in themes if not t.get("has_article")]
    rate = round(deflected / total * 100, 1) if total else 0.0
    coverage = round(sum(1 for t in themes if t.get("has_article")) / len(themes) * 100, 1) if themes else 0.0
    return _out(spec, state, {
        "deflection_rate": rate, "coverage_pct": coverage, "gap_count": len(gaps), "gaps": gaps,
    }, f"Voce e {spec['id']}: deflection {rate}%, {len(gaps)} lacunas de cobertura.", llm)


@register("activation_score")
def activation_score(state, *, llm, store, spec):
    """g9-onboarding-guide — ativação = primeiro outcome ocorreu; % de passos e time-to-value."""
    o = state["task"].get("onboarding", {}) or {}
    total = o.get("steps_total", 0) or 0
    done = o.get("steps_done", 0) or 0
    pct = round(done / total * 100, 1) if total else 0.0
    activated = bool(o.get("first_outcome"))
    days = o.get("days_elapsed", 0) or 0
    target = o.get("target_days", 7) or 7
    on_time = days <= target
    status = "ativado" if activated else ("em_risco" if not on_time else "em_andamento")
    return _out(spec, state, {
        "activated": activated, "activation_pct": pct, "time_to_value_days": days,
        "on_time": on_time, "status": status,
    }, f"Voce e {spec['id']}: ativado={activated}, {pct}% dos passos, {days}d (alvo {target}d).", llm)


@register("refund_eligibility")
def refund_eligibility(state, *, llm, store, spec):
    """g9-refund-handler — elegibilidade por política + flag de fraude; SEMPRE gate humano antes de pagar."""
    r = state["task"].get("refund", {}) or {}
    days = r.get("days_since_purchase", 0) or 0
    window = r.get("policy_window_days", 30) or 30
    fraud = bool(r.get("fraud_flag"))
    if fraud:
        eligible, decision, reason = False, "flag_fraude", "Indício de abuso — encaminhar a fraude antes de pagar"
    elif days <= window:
        eligible, decision, reason = True, "aprovar_com_gate", "Dentro da janela de política"
    else:
        eligible, decision, reason = False, "negar_fora_politica", f"Fora da janela ({days}d > {window}d)"
    return _out(spec, state, {
        "eligible": eligible, "decision": decision, "requires_human_gate": True, "reason": reason,
    }, f"Voce e {spec['id']}: {decision} (gate humano obrigatório).", llm)


@register("sentiment_score")
def sentiment_score(state, *, llm, store, spec):
    """g9-sentiment-monitor — sentimento médio dos sinais e alerta ao cruzar o threshold."""
    s = state["task"].get("sentiment", {}) or {}
    signals = [x.get("polarity", 0) for x in (s.get("signals", []) or [])]
    threshold = s.get("threshold", -0.2)
    score = round(sum(signals) / len(signals), 3) if signals else 0.0
    alert = score < threshold
    status = "negativo" if score < -0.2 else ("positivo" if score > 0.2 else "neutro")
    return _out(spec, state, {
        "sentiment_score": score, "alert_raised": alert, "signal_count": len(signals), "status": status,
    }, f"Voce e {spec['id']}: sentimento {score}, alerta={alert}.", llm)


@register("voc_priority")
def voc_priority(state, *, llm, store, spec):
    """g9-voice-of-customer — prioriza fricções por impacto (frequência × severidade)."""
    v = state["task"].get("voc", {}) or {}
    items = v.get("items", []) or []
    ranked = sorted(
        ({"theme": i.get("theme"), "impact": (i.get("frequency", 0) or 0) * (i.get("severity", 0) or 0)}
         for i in items),
        key=lambda x: -x["impact"])
    return _out(spec, state, {
        "item_count": len(items), "top_theme": ranked[0]["theme"] if ranked else None,
        "ranked": ranked,
    }, f"Voce e {spec['id']}: {len(items)} temas, top '{ranked[0]['theme'] if ranked else '-'}'.", llm)
